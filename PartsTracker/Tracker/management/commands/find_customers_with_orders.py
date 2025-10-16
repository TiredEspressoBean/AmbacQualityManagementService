from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from Tracker.models import User, Orders, OrdersStatus


class Command(BaseCommand):
    help = 'Find customers who have orders in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--active-only',
            action='store_true',
            help='Only show customers with non-completed, non-cancelled orders',
        )
        parser.add_argument(
            '--status',
            type=str,
            choices=[status[0] for status in OrdersStatus.choices],
            help='Filter by specific order status',
        )
        parser.add_argument(
            '--min-orders',
            type=int,
            default=1,
            help='Minimum number of orders (default: 1)',
        )

    def handle(self, *args, **options):
        active_only = options['active_only']
        status_filter = options['status']
        min_orders = options['min_orders']

        # Build query
        query = Q(customer_orders__isnull=False)
        
        if active_only:
            query &= ~Q(customer_orders__order_status__in=[
                OrdersStatus.COMPLETED, 
                OrdersStatus.CANCELLED
            ])
        
        if status_filter:
            query &= Q(customer_orders__order_status=status_filter)

        # Get customers with order counts
        customers = User.objects.filter(query).annotate(
            order_count=Count('customer_orders', distinct=True)
        ).filter(
            order_count__gte=min_orders
        ).select_related('parent_company').prefetch_related('customer_orders')

        if not customers.exists():
            self.stdout.write(
                self.style.WARNING('No customers found matching the criteria.')
            )
            return

        self.stdout.write("=" * 80)
        self.stdout.write(f"CUSTOMERS WITH ORDERS")
        if active_only:
            self.stdout.write("(Active orders only)")
        if status_filter:
            self.stdout.write(f"(Status: {status_filter})")
        self.stdout.write("=" * 80)

        total_customers = 0
        total_orders = 0

        for customer in customers.order_by('parent_company__name', 'last_name', 'first_name'):
            total_customers += 1
            
            # Get orders for this customer based on filters
            orders_query = customer.customer_orders.all()
            
            if active_only:
                orders_query = orders_query.exclude(
                    order_status__in=[OrdersStatus.COMPLETED, OrdersStatus.CANCELLED]
                )
            
            if status_filter:
                orders_query = orders_query.filter(order_status=status_filter)
            
            orders = orders_query.order_by('-created_at')
            order_count = orders.count()
            total_orders += order_count

            # Customer info
            company_name = customer.parent_company.name if customer.parent_company else "No Company"
            self.stdout.write(
                f"\n{customer.first_name} {customer.last_name} ({customer.email})"
            )
            self.stdout.write(f"  Company: {company_name}")
            self.stdout.write(f"  Orders: {order_count}")

            # Show recent orders
            recent_orders = orders[:5]  # Show up to 5 most recent
            for order in recent_orders:
                parts_count = order.parts.count()
                self.stdout.write(
                    f"    - {order.name} ({order.get_order_status_display()}) "
                    f"- {parts_count} parts - Created: {order.created_at.date()}"
                )
            
            if orders.count() > 5:
                self.stdout.write(f"    ... and {orders.count() - 5} more orders")

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Total customers found: {total_customers}")
        self.stdout.write(f"Total orders: {total_orders}")
        
        if total_customers > 0:
            avg_orders = total_orders / total_customers
            self.stdout.write(f"Average orders per customer: {avg_orders:.1f}")