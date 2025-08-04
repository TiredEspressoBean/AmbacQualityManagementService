# Tracker/management/commands/send_weekly_emails.py
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from Tracker.models import User, Orders, OrdersStatus


class Command(BaseCommand):
    help = 'Send weekly order updates to customers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what emails would be sent without actually sending them',
        )
        parser.add_argument(
            '--preview',
            type=str,
            help='Show full email preview for a specific customer email address',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        preview_email = options.get('preview')

        if preview_email:
            self.show_email_preview(preview_email)
            return

        # Rest of existing code...
        active_statuses = [
            OrdersStatus.RFI,
            OrdersStatus.PENDING,
            OrdersStatus.IN_PROGRESS,
            OrdersStatus.ON_HOLD
        ]

        customers_with_orders = User.objects.filter(
            customer_orders__archived=False,
            customer_orders__order_status__in=active_statuses
        ).distinct()

        sent_count = 0

        for customer in customers_with_orders:
            # Get customer's active orders
            active_orders = Orders.objects.filter(
                customer=customer,
                archived=False,
                order_status__in=active_statuses
            ).select_related('company').prefetch_related('parts__step')

            if not active_orders.exists():
                continue

            # Prepare email data
            email_data = self.prepare_order_data(active_orders)

            if dry_run:
                self.stdout.write(f"Would send email to: {customer.email}")
                self.stdout.write(f"Orders: {[order.name for order in active_orders]}")
                continue

            # Send email
            try:
                self.send_customer_email(customer, email_data)
                sent_count += 1
                self.stdout.write(f"✓ Sent update to {customer.email}")
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Failed to send to {customer.email}: {e}")
                )

        if dry_run:
            self.stdout.write(f"Dry run complete. Would send {sent_count} emails.")
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully sent updates to {sent_count} customers')
            )

    def prepare_order_data(self, orders):
        """Prepare simplified order data for email"""
        order_summaries = []

        for order in orders:
            # Get simple stats
            total_parts = order.parts.count()
            completed_parts = order.parts.filter(part_status='COMPLETED').count()

            # Calculate progress percentage
            progress = (completed_parts / total_parts * 100) if total_parts > 0 else 0

            # Get current stage
            current_stage = "Not Started"
            if order.parts.exists():
                # Get the most common step name
                first_part = order.parts.first()
                if first_part and first_part.step:
                    current_stage = first_part.step.name

            order_summaries.append({
                'name': order.name,
                'status': order.get_order_status_display(),
                'progress': round(progress),
                'current_stage': current_stage,
                'completion_date': order.estimated_completion,
                'total_parts': total_parts,
                'completed_parts': completed_parts,
            })

        return order_summaries

    def send_customer_email(self, customer, order_data):
        """Send weekly update email to customer"""
        context = {
            'customer': customer,
            'orders': order_data,
            'week_ending': timezone.now().date(),
            'total_orders': len(order_data),
        }

        # Render email
        subject = f"Weekly Order Update - {timezone.now().strftime('%B %d, %Y')}"
        html_content = render_to_string('emails/weekly_customer_update.html', context)
        text_content = render_to_string('emails/weekly_customer_update.txt', context)

        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'orders@yourcompany.com'),
            recipient_list=[customer.email],
            html_message=html_content,
            fail_silently=False,
        )

    def show_email_preview(self, email):
        """Show full email preview for a specific customer"""
        try:
            customer = User.objects.get(email=email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Customer with email {email} not found'))
            return

        # Get customer's active orders
        active_statuses = [
            OrdersStatus.RFI,
            OrdersStatus.PENDING,
            OrdersStatus.IN_PROGRESS,
            OrdersStatus.ON_HOLD
        ]

        active_orders = Orders.objects.filter(
            customer=customer,
            archived=False,
            order_status__in=active_statuses
        ).select_related('company').prefetch_related('parts__step')

        if not active_orders.exists():
            self.stdout.write(f'No active orders found for {email}')
            return

        # Prepare email data
        email_data = self.prepare_order_data(active_orders)

        context = {
            'customer': customer,
            'orders': email_data,
            'week_ending': timezone.now().date(),
            'total_orders': len(email_data),
        }

        # Render templates
        subject = f"Weekly Order Update - {timezone.now().strftime('%B %d, %Y')}"

        try:
            html_content = render_to_string('emails/weekly_customer_update.html', context)
            text_content = render_to_string('emails/weekly_customer_update.txt', context)

            # Display preview
            self.stdout.write('=' * 60)
            self.stdout.write(f'EMAIL PREVIEW FOR: {customer.email}')
            self.stdout.write('=' * 60)
            self.stdout.write(f'TO: {customer.email}')
            self.stdout.write(f'SUBJECT: {subject}')
            self.stdout.write('-' * 60)
            self.stdout.write('TEXT VERSION:')
            self.stdout.write('-' * 60)
            self.stdout.write(text_content)
            self.stdout.write('-' * 60)
            self.stdout.write('HTML VERSION (first 1000 chars):')
            self.stdout.write('-' * 60)
            self.stdout.write(html_content[:1000] + '...' if len(html_content) > 1000 else html_content)
            self.stdout.write('=' * 60)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Template error: {e}'))