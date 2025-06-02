from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from orders.models import Order
from shipping.models import Shipment # Assuming Shipment model exists
import random

class Command(BaseCommand):
    help = 'Populates the database with sample shipment data'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating shipments...")

        # Only create shipments for orders that are shipped or delivered
        shippable_orders = list(Order.objects.filter(status__in=['shipped', 'delivered']))
        
        if not shippable_orders:
            self.stdout.write(self.style.WARNING('No orders found with status "shipped" or "delivered". Skipping shipment creation.'))
            return

        shipments_to_create = []
        shipping_carriers = ['DHL', 'FedEx', 'UPS', 'Aramex', 'Local Post']

        for order in shippable_orders:
            # Shipment date should be after order creation, and before or on order update (if delivered)
            shipment_date = fake.date_time_between(start_date=order.created_at, end_date=order.updated_at, tzinfo=timezone.get_current_timezone())
            if shipment_date > order.updated_at: # ensure it's not after the final update
                shipment_date = order.updated_at
            
            # Estimated delivery date
            estimated_delivery_date = shipment_date + timezone.timedelta(days=random.randint(1, 10))
            
            # Actual delivery date (only if order is delivered)
            actual_delivery_date = None
            if order.status == 'delivered':
                # Ensure actual delivery is after or on shipment_date and not much later than estimated
                min_delivery_time = shipment_date
                max_delivery_time = estimated_delivery_date + timezone.timedelta(days=2) # Allow some buffer
                if order.updated_at > min_delivery_time : # if order was updated after shipping, use that
                    min_delivery_time = order.updated_at

                actual_delivery_date = fake.date_time_between(start_date=min_delivery_time, end_date=max_delivery_time, tzinfo=timezone.get_current_timezone())
                if actual_delivery_date > timezone.now(): # Cannot be in future
                    actual_delivery_date = timezone.now()
                if actual_delivery_date < shipment_date: # Must be after shipment
                    actual_delivery_date = shipment_date


            shipments_to_create.append(Shipment(
                order=order,
                tracking_number=fake.unique.bothify(text='??########??'), # Example tracking format
                carrier=random.choice(shipping_carriers),
                shipped_at=shipment_date, # Changed from shipped_date
                estimated_delivery=estimated_delivery_date, # Changed from estimated_delivery_date
                actual_delivery_date=actual_delivery_date,
                # Assuming address details are on the order, or a snapshot is taken here if needed
                # shipping_address_snapshot = order.shipping_address_snapshot (if needed on shipment model itself)
                status='in_transit' if order.status == 'shipped' else order.status # Map 'shipped' to 'in_transit' for Shipment
            ))
        
        Shipment.objects.bulk_create(shipments_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Shipment.objects.count()} shipments.'))
