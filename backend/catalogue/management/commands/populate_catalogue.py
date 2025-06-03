from django.core.management.base import BaseCommand
from django.utils.text import slugify
from faker import Faker
from catalogue.models import Category, Product, ProductImage
from vendors.models import Vendor
import random

class Command(BaseCommand):
    help = 'Populates the database with sample catalogue data (Categories, Products, ProductImages)'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Creating categories...")

        categories_to_create = []
        for _ in range(random.randint(20, 50)): # 20-50 categories
            name = fake.unique.bs() # Using bs for category names
            name_for_slug = name[:40] # Truncate for slug generation
            slug = slugify(name_for_slug)
            original_slug = slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{original_slug}-{counter}"
                counter += 1

            categories_to_create.append(Category(
                name=name,
                slug=slug,
                description=fake.text(max_nb_chars=200),
                # parent category - will handle hierarchy in a second pass for simplicity
            ))

        Category.objects.bulk_create(categories_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {Category.objects.count()} base categories.'))

        # Assign parent categories randomly for some
        all_categories = list(Category.objects.all())
        if len(all_categories) > 1:
            for category in all_categories:
                if random.random() < 0.3: # 30% chance to have a parent
                    possible_parents = [p for p in all_categories if p.id != category.id]
                    if possible_parents:
                        category.parent = random.choice(possible_parents)
                        category.save()
            self.stdout.write(self.style.SUCCESS('Assigned parent categories for some categories.'))


        self.stdout.write("Creating products...")
        all_vendors = list(Vendor.objects.filter(status='active'))
        if not all_vendors:
            self.stdout.write(self.style.ERROR('No active vendors found. Cannot create products.'))
            return # Exit if no active vendors

        if not all_categories:
            self.stdout.write(self.style.ERROR('No categories found. Cannot create products.'))
            return

        products_to_create = []
        num_products = random.randint(5000, 10000)
        for i in range(num_products):
            if i % 500 == 0 and i > 0:
                self.stdout.write(f"Preparing product {i} of {num_products}...")

            name = fake.name() # Placeholder for product name
            name_for_slug = name[:30] # Truncate for slug generation
            slug = slugify(name_for_slug)
            original_slug = slug
            counter = 1
            while Product.objects.filter(slug=slug).exists(): # This check can be slow in a loop
                slug = f"{original_slug}-{counter}-{random.randint(1000,9999)}" # Add random int to ensure uniqueness faster
                counter += 1

            # JSON attributes
            attributes = {
                "color": fake.color_name(),
                "size": random.choice(["S", "M", "L", "XL"]),
                "material": fake.word(),
                "warranty": f"{random.randint(1, 3)} years"
            }

            product_data = {
                "name": name,
                "slug": slug,
                "description": fake.text(max_nb_chars=1000),
                "category": random.choice(all_categories),
                "vendor": random.choice(all_vendors) if all_vendors else None,
                "sku": fake.unique.ean13(), # Ensure unique SKU
                "price": round(random.uniform(10, 1000), 2),
                "stock_quantity": random.randint(0, 200),
                "is_active": random.choices([True, False], weights=[0.9, 0.1], k=1)[0],
                "attributes": attributes, # Store as JSON string
                "weight": round(random.uniform(0.1, 50), 2) if random.choice([True, False]) else None,
                "dimensions": f"{random.randint(1,100)}x{random.randint(1,100)}x{random.randint(1,100)}" if random.choice([True, False]) else None, # LxWxH cm
            }
            # This loop with filter().exists() is slow for large numbers.
            # A better approach for very large numbers might involve pre-generating slugs or handling IntegrityError.
            # For now, proceeding with this, but noting it as a performance bottleneck.
            try:
                products_to_create.append(Product(**product_data))
            except Exception as e: # Catch if SKU is not unique, though fake.unique should handle it
                 self.stdout.write(self.style.WARNING(f"Could not prepare product {name} due to {e}. SKU: {product_data.get('sku')}"))


        # Bulk create products in batches to manage memory and potential signal issues
        batch_size = 500
        for i in range(0, len(products_to_create), batch_size):
            batch = products_to_create[i:i + batch_size]
            Product.objects.bulk_create(batch, ignore_conflicts=True) # ignore_conflicts for slugs/skus if uniqueness check above fails
            self.stdout.write(f"Created batch of {len(batch)} products...")

        total_products_created = Product.objects.count()
        self.stdout.write(self.style.SUCCESS(f'Successfully created {total_products_created} products.'))

        self.stdout.write("Creating product images...")
        all_products = list(Product.objects.all()) # Re-fetch to get IDs
        product_images_to_create = []
        for product in all_products:
            num_images = random.randint(1, 4)
            for i in range(num_images):
                # Using placeholder paths as per requirements
                image_path = f"/tmp/placeholder_image_{product.slug}_{i+1}.png"
                product_images_to_create.append(ProductImage(
                    product=product,
                    image=image_path, # Assuming ImageField can take a path string
                    alt_text=f"Image {i+1} for {product.name[:220]}", # Truncate product name for alt_text
                    is_primary=(i == 0) # First image is primary
                ))

        # Bulk create product images
        ProductImage.objects.bulk_create(product_images_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {ProductImage.objects.count()} product images.'))

        self.stdout.write(self.style.SUCCESS('Successfully populated catalogue.'))
