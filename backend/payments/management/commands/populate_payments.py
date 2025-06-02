from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from orders.models import Order
from payments.models import Payment # Assuming Payment model exists
import random

class Command(BaseCommand):
    help = 'Populates the database with sample payment data'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating payments...")

        orders = list(Order.objects.all())
        if not orders:
            self.stdout.write(self.style.WARNING('No orders found. Skipping payment creation.'))
            return

        payments_to_create = []
        for order in orders:
            # Determine payment status based on order status
            if order.status in ['cancelled', 'refunded', 'pending']:
                payment_status = 'pending' # or 'failed' if cancelled early
                if order.status == 'refunded':
                    payment_status = 'refunded'
            elif order.status in ['processing', 'shipped', 'delivered']:
                payment_status = 'paid' # Changed from 'completed' to 'paid'
            else: # Default for any other status
                payment_status = 'pending'

            # If order is delivered or shipped, payment must be paid
            if order.status in ['delivered', 'shipped'] and payment_status != 'paid': # Changed from 'completed'
                 # This case should ideally not happen if logic is consistent
                 # but as a fallback:
                 payment_status = 'paid' # Changed from 'completed'


            transaction_id = fake.unique.ean(length=13) # Using EAN as a placeholder for transaction_id
            
            # Payment date should align with order date, or slightly after for processing
            payment_date = order.created_at + timezone.timedelta(minutes=random.randint(1, 60)) if order.status != 'pending' else order.created_at
            if payment_date > timezone.now():
                payment_date = timezone.now()
            
            # For refunded payments
            if payment_status == 'refunded' and order.updated_at > payment_date:
                payment_date = order.updated_at


            payments_to_create.append(Payment(
                order=order,
                amount=order.total_amount,
                method=order.payment_method, # Changed from payment_method to method
                transaction_id=transaction_id,
                status=payment_status, # This should align with Payment.PAYMENT_STATUS choices
                payment_date=payment_date
                # additional_details: e.g. last 4 digits of a card, could be faked too
            ))

        Payment.objects.bulk_create(payments_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Payment.objects.count()} payments.'))
