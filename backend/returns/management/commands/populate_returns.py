from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from orders.models import Order, OrderItem
from returns.models import ReturnRequest, ReturnItem # Assuming these models exist
import random

class Command(BaseCommand):
    help = 'Populates the database with sample return requests and items'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating return requests...")

        # Consider returns only for delivered orders
        delivered_orders = list(Order.objects.filter(status='delivered'))
        
        if not delivered_orders:
            self.stdout.write(self.style.WARNING('No "delivered" orders found. Skipping return request creation.'))
            return

        num_return_requests = random.randint(50, 100)
        return_requests_created_count = 0
        return_items_created_count = 0
        
        possible_reasons = ['item_damaged', 'wrong_item', 'changed_mind', 'does_not_fit', 'quality_not_as_expected']
        possible_statuses = ['pending', 'approved', 'rejected', 'processing', 'completed'] # For the return itself

        orders_for_returns = random.sample(delivered_orders, k=min(num_return_requests, len(delivered_orders)))

        for order in orders_for_returns:
            order_items = list(order.items.all()) # Assuming related_name is 'items' for OrderItem on Order
            if not order_items:
                continue

            # Return request date should be after order delivery date
            # Assuming order.actual_delivery_date is available or can be inferred from order.updated_at for delivered orders
            # For simplicity, let's base it on order.updated_at as a proxy for delivery time
            min_return_request_date = order.updated_at + timezone.timedelta(days=1)
            max_return_request_date = min_return_request_date + timezone.timedelta(days=30) # Within 30 days of delivery
            
            if max_return_request_date > timezone.now():
                max_return_request_date = timezone.now()
            
            if min_return_request_date > max_return_request_date: # If order was delivered very recently
                 min_return_request_date = max_return_request_date - timezone.timedelta(days=1)


            request_date = fake.date_time_between(start_date=min_return_request_date, end_date=max_return_request_date, tzinfo=timezone.get_current_timezone())
            
            return_status = random.choice(possible_statuses)

            try:
                return_request = ReturnRequest.objects.create(
                    order=order,
                    user=order.user, # Assuming user is on order
                    reason_text=fake.sentence(),
                    status=return_status,
                    requested_date=request_date,
                    # updated_at will be set by model's auto_now=True
                )
                return_requests_created_count += 1

                # Select some items from the order to be returned
                num_items_to_return = random.randint(1, len(order_items))
                items_to_return_in_this_request = random.sample(order_items, k=num_items_to_return)

                for item in items_to_return_in_this_request:
                    ReturnItem.objects.create(
                        return_request=return_request,
                        order_item=item,
                        quantity=random.randint(1, item.quantity), # Return some or all quantity of that item
                        reason=random.choice(possible_reasons) 
                        # condition (e.g. 'opened', 'unopened') could be another field
                    )
                    return_items_created_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating return request for order {order.id}: {e}"))


        self.stdout.write(self.style.SUCCESS(f'Successfully created {return_requests_created_count} return requests and {return_items_created_count} return items.'))
