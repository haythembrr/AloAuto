from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings # Required for settings.AUTH_USER_MODEL
from faker import Faker
from orders.models import Order, OrderItem
from returns.models import Return # Target model
# from accounts.models import User # Not strictly needed if using order.user
import random

class Command(BaseCommand):
    help = 'Populates the database with sample return data against OrderItems'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating Return entries...")

        # Consider returns only for delivered orders that have items
        delivered_orders = Order.objects.filter(status='delivered').prefetch_related('items')

        if not delivered_orders.exists():
            self.stdout.write(self.style.WARNING('No "delivered" orders with items found. Skipping return creation.'))
            return

        returns_to_create = []
        target_num_returns = random.randint(50, 100)
        returns_created_count = 0

        # Get choices directly from the Return model
        reason_choices = [choice[0] for choice in Return.RETURN_REASON]
        status_choices = [choice[0] for choice in Return.RETURN_STATUS]

        # Loop until we have enough returns or run out of orders/items
        # This is to ensure we don't try to sample more orders than available if list is small
        order_pool = list(delivered_orders)
        random.shuffle(order_pool) # Shuffle to get random orders

        for order in order_pool:
            if returns_created_count >= target_num_returns:
                break

            order_items = list(order.items.all())
            if not order_items:
                continue

            # Decide how many items from this order to return (1 to all, or a subset)
            num_items_from_order_to_return = random.randint(1, min(len(order_items), 3)) # Return up to 3 items from an order
            items_to_process_for_return = random.sample(order_items, k=num_items_from_order_to_return)

            for item in items_to_process_for_return:
                if returns_created_count >= target_num_returns:
                    break

                # requested_date: after delivery (order.updated_at) but before now
                # Assuming order.updated_at is a reliable proxy for delivery date for 'delivered' orders
                min_request_date = order.updated_at + timezone.timedelta(days=1)
                # Max request date: up to 30 days after delivery, but not in future
                max_request_date = min_request_date + timezone.timedelta(days=random.randint(1,30))

                if max_request_date > timezone.now():
                    max_request_date = timezone.now()

                # Ensure min_request_date is not after max_request_date
                if min_request_date > max_request_date:
                    # This can happen if order was delivered very recently (e.g. today)
                    # In this case, make request_date = max_request_date (i.e. now or slightly before)
                    if order.updated_at > timezone.now() : # if order updated_at is somehow in future
                         min_request_date = timezone.now() - timezone.timedelta(hours=1)
                    else:
                        min_request_date = order.updated_at

                    if min_request_date > max_request_date : # still an issue
                        requested_date_val = max_request_date
                    else:
                        requested_date_val = fake.date_time_between(start_date=min_request_date, end_date=max_request_date, tzinfo=timezone.get_current_timezone())

                else:
                     requested_date_val = fake.date_time_between(start_date=min_request_date, end_date=max_request_date, tzinfo=timezone.get_current_timezone())


                quantity_to_return = random.randint(1, item.quantity)

                # Calculate refund_amount (optional, can be null)
                # Ensure item.price_at_purchase is available and not None
                calculated_refund_amount = None
                if item.price_at_purchase is not None: # Or use unit_price if that's more appropriate
                    calculated_refund_amount = round(quantity_to_return * item.price_at_purchase, 2)

                return_instance_data = {
                    "order": order,
                    "order_item": item,
                    "user": order.user, # User who made the order
                    "reason": random.choice(reason_choices),
                    "status": random.choice(status_choices),
                    "description": fake.sentence(nb_words=10),
                    "requested_date": requested_date_val,
                    "quantity_returned": quantity_to_return,
                    "refund_amount": calculated_refund_amount
                }
                returns_to_create.append(Return(**return_instance_data))
                returns_created_count += 1

        if returns_to_create:
            Return.objects.bulk_create(returns_to_create)
            self.stdout.write(self.style.SUCCESS(f'Successfully created {len(returns_to_create)} Return entries.'))
        else:
            self.stdout.write(self.style.WARNING('No Return entries were generated.'))
