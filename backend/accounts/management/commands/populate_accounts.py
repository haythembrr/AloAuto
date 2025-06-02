from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from faker import Faker
from accounts.models import User, Address
import random

class Command(BaseCommand):
    help = 'Populates the database with sample account and address data'

    def handle(self, *args, **options):
        fake = Faker() # Consider Faker('tn_TN') if available and relevant. Using generic for now.
        STANDARD_PASSWORD = "password123" # Consistent password for test users

        self.stdout.write("Creating users...")
        
        users_to_create_spec = [
            {"username": "admin_test_api_user", "email": "admintest@example.com", "user_type": "admin", "is_staff": True, "is_superuser": True},
            {"username": "vendor_test_api_user", "email": "vendortest@example.com", "user_type": "vendor", "is_staff": False, "is_superuser": False},
            {"username": "vendor2_test_api_user", "email": "vendor2test@example.com", "user_type": "vendor", "is_staff": False, "is_superuser": False},
            {"username": "buyer_test_api_user", "email": "buyertest@example.com", "user_type": "buyer", "is_staff": False, "is_superuser": False},
        ]

        users = []

        for spec in users_to_create_spec:
            if not User.objects.filter(username=spec["username"]).exists():
                users.append(User(
                    username=spec["username"],
                    email=spec["email"],
                    password=make_password(STANDARD_PASSWORD),
                    first_name=fake.first_name(),
                    last_name=fake.last_name(),
                    phone_number=fake.phone_number(),
                    is_staff=spec["is_staff"],
                    is_superuser=spec["is_superuser"],
                    user_type=spec["user_type"]
                ))
            else:
                self.stdout.write(self.style.WARNING(f"User {spec['username']} already exists. Skipping creation."))

        # Create additional Admin Users
        # Ensure we have at least 3 admins in total, including the test API admin user.
        num_additional_admins = 3 - sum(1 for spec in users_to_create_spec if spec["user_type"] == "admin")
        for i in range(num_additional_admins):
            username = f"admin_{fake.user_name()}"
            while User.objects.filter(username=username).exists():
                username = f"admin_{fake.user_name()}"
            email = fake.email()
            while User.objects.filter(email=email).exists(): # Check for email uniqueness too
                email = fake.email()
            users.append(User(
                username=username,
                email=email,
                password=make_password(STANDARD_PASSWORD),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=fake.phone_number(), 
                is_staff=True,
                is_superuser=True,
                user_type='admin'
            ))

        # Create additional Vendor Users
        # Ensure we have at least 100 vendors, including specific test API vendors.
        num_additional_vendors = 100 - sum(1 for spec in users_to_create_spec if spec["user_type"] == "vendor")
        for i in range(num_additional_vendors):
            username = f"vendor_{fake.user_name()}"
            while User.objects.filter(username=username).exists():
                username = f"vendor_{fake.user_name()}"
            email = fake.email()
            while User.objects.filter(email=email).exists(): # Check for email uniqueness too
                email = fake.email()
            users.append(User(
                username=username,
                email=email,
                password=make_password(STANDARD_PASSWORD),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=fake.phone_number(),
                is_staff=False,
                is_superuser=False,
                user_type='vendor'
            ))
        
        # Create additional Buyer Users
        # Aim for ~1000 users total. Current count is len(users).
        # remaining_users = 1000 - User.objects.count() - len(users) # This line is problematic as users are not yet created
        # Let's calculate based on what we plan to create vs target total
        
        # Calculate how many users we have specified or are planning to create so far
        current_planned_users = len(users) # This includes specific test users and additional admins/vendors
        
        # Target total users (approx)
        total_target_users = 1000
        
        # How many more buyers to create
        num_additional_buyers = total_target_users - current_planned_users
        if num_additional_buyers < 0: # If we already met target with admins/vendors
            num_additional_buyers = 0
            
        self.stdout.write(f"Planning to create {num_additional_buyers} additional buyer users.")

        for i in range(num_additional_buyers):
            username = fake.user_name()
            # Ensure username is unique
            temp_username = username
            counter = 0
            while User.objects.filter(username=temp_username).exists() or any(u.username == temp_username for u in users):
                counter += 1
                temp_username = f"{username}_{counter}"
            username = temp_username
            
            email = fake.email()
            temp_email = email
            counter = 0
            # Ensure email is unique among existing DB users and users about to be created
            while User.objects.filter(email=temp_email).exists() or any(u.email == temp_email for u in users):
                counter +=1
                temp_email = f"{counter}{email}" # Prepending counter to change it more significantly
            email = temp_email
            
            users.append(User(
                username=username,
                email=email,
                password=make_password(STANDARD_PASSWORD),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                phone_number=fake.phone_number(), # Generic phone number
                is_staff=False,
                is_superuser=False,
                user_type='buyer'
            ))
        
        User.objects.bulk_create(users, ignore_conflicts=True) # ignore_conflicts might hide issues with username/email generation if not careful
        self.stdout.write(self.style.SUCCESS(f'Successfully created {User.objects.count()} users.'))

        self.stdout.write("Creating addresses...")
        # Fetch all users to assign addresses.
        # This is done after user creation to ensure all users, including bulk_created ones, are available.
        all_users = list(User.objects.all())
        addresses = []
        for user in all_users:
            num_addresses = random.randint(1, 3)
            for _ in range(num_addresses):
                addresses.append(Address(
                    user=user,
                    street_address=fake.street_address(),
                    city=fake.city(),
                    state=fake.state(), # Generic state
                    postal_code=fake.postcode(), # Generic postcode
                    country=fake.country(),
                    is_default_shipping=True, # Make one default shipping
                    is_default_billing=True, # Make one default billing
                ))
        
        # For simplicity, bulk_create addresses. If there's complex logic for default addresses, create individually.
        Address.objects.bulk_create(addresses)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Address.objects.count()} addresses.'))

        # To make default addresses unique per user (if needed)
        # This part needs to be more robust if strict single default is required.
        # For now, the last address created for a user via bulk_create might not be the one marked default if there were multiple.
        # A more robust approach would iterate users and set defaults specifically.
        # For now, this script assumes the model or app logic handles ensuring only one default.
        # If not, a post-bulk_create step would be:
        # for user in all_users:
        #   if user.addresses.exists():
        #       addr_to_default = user.addresses.first() # or last(), or random
        #       # Ensure other addresses for this user are not default for shipping/billing
        #       Address.objects.filter(user=user).update(is_default_shipping=False, is_default_billing=False)
        #       addr_to_default.is_default_shipping = True
        #       addr_to_default.is_default_billing = True
        #       addr_to_default.save()

        self.stdout.write(self.style.SUCCESS('Successfully populated accounts and addresses.'))
