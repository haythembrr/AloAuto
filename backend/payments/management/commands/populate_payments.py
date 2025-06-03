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
            # Assuming Order.STATUS_CHOICES are ('new', 'New'), ('confirmed', 'Confirmed'), ('processing', 'Processing'),
            # ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled'), ('refunded', 'Refunded')
            # Assuming Order.STATUS_CHOICES are ('new', 'New'), ('confirmed', 'Confirmed'),
            # ('shipped', 'Shipped'), ('delivered', 'Delivered'), ('cancelled', 'Cancelled')
            # Assuming Payment.PAYMENT_STATUS_CHOICES are ('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed'), ('refunded', 'Refunded')

            order_status_val = order.status

            if order_status_val == 'cancelled':
                payment_status = 'failed'
            elif order_status_val == 'new':
                payment_status = 'pending'
            elif order_status_val == 'confirmed':
                payment_status = 'pending'
            elif order_status_val in ['shipped', 'delivered']:
                payment_status = 'paid'
            else: # Fallback for any other status not explicitly handled
                payment_status = 'pending'

            # Safeguard: If order is definitely paid (e.g., delivered), payment status must be 'paid'
            # This also covers 'shipped' as per above logic.
            if order_status_val in ['shipped', 'delivered'] and payment_status != 'paid':
                payment_status = 'paid'

            # Note: Setting payment_status to 'refunded' would require checking if a 'paid' payment already
            # exists for a now 'cancelled' or 'refunded' order, which is beyond this script's scope.
            # The current Order.status choices given ('new', 'confirmed', 'shipped', 'delivered', 'cancelled')
            # do not include 'refunded', so payment_status will not be set to 'refunded' based on order.status.

            transaction_id = fake.unique.ean(length=13) # Using EAN as a placeholder for transaction_id

            # Payment date should align with order date, or slightly after for processing
            payment_date = order.created_at + timezone.timedelta(minutes=random.randint(1, 60)) if order.status != 'pending' else order.created_at
            if payment_date > timezone.now():
                payment_date = timezone.now()

            # For refunded payments
            if payment_status == 'refunded' and order.updated_at > payment_date:
                payment_date = order.updated_at


            # Determine payment method
            # Assuming Payment.PAYMENT_METHOD_CHOICES are ('credit_card', 'Credit Card'), ('paypal', 'PayPal'), ('cash', 'Cash')
            # Note: 'bank_transfer' is NOT a valid choice for Payment.method as per problem description.
            valid_payment_model_methods = [choice[0] for choice in Payment.PAYMENT_METHOD] # Use actual attribute name
            order_payment_method_value = order.payment_method # This comes from Order model's payment_method field

            if 'card' in order_payment_method_value.lower():
                chosen_method = 'credit_card'
            elif 'paypal' in order_payment_method_value.lower():
                chosen_method = 'paypal'
            elif 'cash' in order_payment_method_value.lower(): # Catches 'cash' and 'cash_on_delivery'
                chosen_method = 'cash'
            else: # Default for unmapped (like 'bank_transfer' from order) or new unknown methods
                chosen_method = 'credit_card' # Fallback to a valid default like 'credit_card'

            # Final check to ensure chosen_method is in the list (guaranteed by above logic if choices are correct)
            if chosen_method not in valid_payment_model_methods:
                # This case should ideally not be reached if Payment.PAYMENT_METHOD_CHOICES is accurate
                # and the above logic correctly maps to one of its values.
                # If it's reached, it implies a mismatch between assumed choices and actual model choices.
                chosen_method = 'credit_card' # Absolute fallback to a known valid method

            payments_to_create.append(Payment(
                order=order,
                amount=order.total_amount,
                method=chosen_method, # This is now one of ('credit_card', 'paypal', 'cash')
                transaction_id=transaction_id,
                status=payment_status,
                payment_date=payment_date
                # additional_details: e.g. last 4 digits of a card, could be faked too
            ))

        Payment.objects.bulk_create(payments_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Payment.objects.count()} payments.'))
