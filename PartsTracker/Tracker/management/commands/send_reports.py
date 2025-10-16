from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from Tracker.models import Orders  # adjust as needed
from Tracker.email_handler import send_weekly_order_report

class Command(BaseCommand):
    help = 'Send weekly order status reports to customers with active orders'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        # one_week_ago = timezone.now() - timedelta(days=7)

        # Get active users who are customers on at least one order
        users_with_orders = User.objects.filter(
            customer_orders__isnull=False,
            is_active=True
        ).distinct()

        for user in users_with_orders:
            orders = Orders.objects.filter(
                customer=user,
                archived=False,
                # updated_at__gte=one_week_ago
            ).order_by('-updated_at')

            if orders.exists():
                self.stdout.write(f"Sending report to: {user.email} ({orders.count()} orders)")
                send_weekly_order_report(user, orders)
            else:
                self.stdout.write(f"Skipping {user.email}, no updated orders.")