from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from accounts.models import User
from orders.models import Order # Optional: link ticket to an order
from support.models import Ticket # Assuming Ticket model exists
import random

class Command(BaseCommand):
    help = 'Populates the database with sample support tickets'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating support tickets...")

        users = list(User.objects.all())
        orders = list(Order.objects.all()) # To optionally link tickets to orders

        if not users:
            self.stdout.write(self.style.WARNING('No users found. Skipping support ticket creation.'))
            return

        num_tickets = random.randint(100, 200)
        tickets_created_count = 0
        
        ticket_subjects = [
            "Issue with my order", "Payment problem", "Delivery delay", 
            "Question about a product", "Account help needed", "Return request query",
            "Website bug report", "Feature request"
        ]
        possible_statuses = ['open', 'in_progress', 'resolved', 'closed', 'pending_customer']
        possible_priorities = ['low', 'medium', 'high', 'urgent']

        for i in range(num_tickets):
            user = random.choice(users)
            subject = random.choice(ticket_subjects)
            status = random.choice(possible_statuses)
            priority = random.choice(possible_priorities)
            
            # Ticket creation date
            created_at = fake.date_time_between(start_date="-1y", end_date="now", tzinfo=timezone.get_current_timezone())
            
            # Updated date: same as created if new, or later if processed
            updated_at = created_at
            if status != 'open': # If it's not a brand new ticket
                updated_at = fake.date_time_between(start_date=created_at, end_date="now", tzinfo=timezone.get_current_timezone())
                if updated_at < created_at: # Ensure updated_at is not before created_at
                    updated_at = created_at

            # Optionally link to an order
            linked_order = None
            if random.random() < 0.4 and orders: # 40% chance to link to an order
                linked_order = random.choice(orders)

            try:
                Ticket.objects.create(
                    user=user,
                    subject=f"{subject} - {fake.unique.ean(length=8)}", # Add unique part to subject
                    description=fake.text(max_nb_chars=500),
                    status=status,
                    priority=priority,
                    created_at=created_at,
                    updated_at=updated_at,
                    order=linked_order 
                    # assigned_to (ForeignKey to an admin/support User) could be added if applicable
                )
                tickets_created_count += 1
            except Exception as e:
                 self.stdout.write(self.style.ERROR(f"Error creating ticket for user {user.username}: {e}"))


        self.stdout.write(self.style.SUCCESS(f'Successfully created {tickets_created_count} support tickets.'))
