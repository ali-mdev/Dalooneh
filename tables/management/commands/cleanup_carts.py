from django.core.management.base import BaseCommand
from django.utils import timezone
from tables.models import TableSession
from orders.models import Order, OrderItem


class Command(BaseCommand):
    help = 'Clean up expired table sessions and their associated cart items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Clean up sessions older than this many days (default: 1)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually deleting anything',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        self.stdout.write(f"Looking for sessions and orders older than {cutoff_date}")
        
        # Find expired sessions
        expired_sessions = TableSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        )
        
        self.stdout.write(f"Found {expired_sessions.count()} active sessions that have expired")
        
        # Deactivate expired sessions and clean up carts
        if not dry_run:
            for session in expired_sessions:
                self.stdout.write(f"Deactivating session {session.token} for table {session.table.number}")
                session.deactivate()
        else:
            self.stdout.write("Dry run - not deactivating sessions")
                
        # Find old pending orders and clean them up
        old_pending_orders = Order.objects.filter(
            status='pending',
            created_at__lt=cutoff_date
        )
        
        self.stdout.write(f"Found {old_pending_orders.count()} pending orders older than {days} days")
        
        if not dry_run:
            # Clean up old pending orders
            item_count = 0
            for order in old_pending_orders:
                # Count items before deleting
                order_items = order.items.all()
                order_item_count = order_items.count()
                item_count += order_item_count
                
                self.stdout.write(f"Cleaning up order {order.id} with {order_item_count} items for table {order.table.number}")
                
                # Delete items
                order_items.delete()
                
                # Update order status
                order.status = 'cancelled'
                order.total_amount = 0
                order.final_amount = 0
                order.save(update_fields=['status', 'total_amount', 'final_amount'])
            
            self.stdout.write(self.style.SUCCESS(f"Successfully cleaned up {old_pending_orders.count()} orders and {item_count} items"))
        else:
            self.stdout.write("Dry run - not deleting any orders or items")
        
        # Output summary
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would clean' if dry_run else 'Cleaned'} {expired_sessions.count()} expired sessions "
                f"and {old_pending_orders.count()} old pending orders"
            )
        ) 