from django.core.management.base import BaseCommand
from faker import Faker
from django.utils.text import slugify
from accounts.models import User
from vendors.models import Vendor
import random

class Command(BaseCommand):
    help = 'Populates the database with sample vendor data'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating vendors...")

        vendor_users = User.objects.filter(role='vendor')
        if not vendor_users.exists():
            self.stdout.write(self.style.WARNING('No vendor users found. Please populate accounts first.'))
            return

        vendors_to_create = []
        for user in vendor_users:
            company_name = fake.company()
            # Ensure unique slug
            slug = slugify(company_name)
            original_slug = slug
            counter = 1
            while Vendor.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1

            # Ensure unique tax number
            tax_number = fake.bothify(text='TN#########') # Example format
            while Vendor.objects.filter(tax_number=tax_number).exists():
                tax_number = fake.bothify(text='TN#########')


            vendors_to_create.append(Vendor(
                user=user,
                company_name=company_name,
                slug=slug,
                description=fake.text(max_nb_chars=500),
                contact_email=user.email, # Or a different contact email
                contact_phone=user.phone, # Or a different contact phone
                address=fake.address(), # This might need to be structured if Address model is linked
                website=fake.url() if random.choice([True, False]) else None,
                status=random.choice([s[0] for s in Vendor.STATUS_CHOICES]),
                tax_number=tax_number,
                registration_date=fake.past_date(),
                # logo - skip for now, or use a placeholder path if model allows
            ))

        Vendor.objects.bulk_create(vendors_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Vendor.objects.count()} vendors.'))
