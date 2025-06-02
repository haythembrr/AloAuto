from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from accounts.models import User
from catalogue.models import Product
from orders.models import Cart, CartItem, Wishlist, Order, OrderItem
import random

class Command(BaseCommand):
    help = 'Populates the database with sample order data (Carts, Wishlists, Orders)'

    def handle(self, *args, **options):
        fake = Faker()
        self.stdout.write("Starting to populate order-related data...")

        buyer_users = list(User.objects.filter(user_type='buyer'))
        all_products = list(Product.objects.filter(is_active=True))

        if not buyer_users:
            self.stdout.write(self.style.WARNING('No buyer users found. Skipping order data population.'))
            return
        if not all_products:
            self.stdout.write(self.style.WARNING('No active products found. Skipping order data population.'))
            return

        # Create Carts & CartItems
        self.stdout.write("Creating carts and cart items...")
        carts_created_count = 0
        cart_items_created_count = 0
        users_for_cart = random.sample(buyer_users, k=int(len(buyer_users) * random.uniform(0.5, 0.7)))
        
        for user in users_for_cart:
            cart, created = Cart.objects.get_or_create(user=user) # Assuming Cart has a OneToOne or ForeignKey to User
            if created:
                carts_created_count +=1
            
            num_cart_items = random.randint(1, 5)
            products_in_cart = random.sample(all_products, k=min(num_cart_items, len(all_products)))
            
            for product in products_in_cart:
                if product.stock_quantity > 0:
                    quantity = random.randint(1, min(5, product.stock_quantity))
                    CartItem.objects.create(cart=cart, product=product, quantity=quantity)
                    cart_items_created_count += 1
        self.stdout.write(self.style.SUCCESS(f'Successfully created {carts_created_count} carts and {cart_items_created_count} cart items.'))

        # Create Wishlists
        self.stdout.write("Creating wishlists...")
        wishlists_created_count = 0
        users_for_wishlist = random.sample(buyer_users, k=int(len(buyer_users) * random.uniform(0.3, 0.5)))
        wishlists_to_create = []
        for user in users_for_wishlist:
            # Assuming Wishlist model has a ForeignKey or OneToOne to User and ManyToMany to Product
            wishlist, created = Wishlist.objects.get_or_create(user=user)
            if created:
                wishlists_created_count +=1
            
            num_wishlist_items = random.randint(1, 10)
            products_in_wishlist = random.sample(all_products, k=min(num_wishlist_items, len(all_products)))
            wishlist.products.add(*products_in_wishlist) # Add products to ManyToManyField
            
        self.stdout.write(self.style.SUCCESS(f'Successfully created {wishlists_created_count} wishlists and added items to them.'))

        # Create Orders & OrderItems
        self.stdout.write("Creating orders and order items...")
        orders_to_create = []
        order_items_to_create = []
        num_orders = random.randint(500, 1000)
        
        possible_order_statuses = ['pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded']

        for i in range(num_orders):
            if i % 100 == 0 and i > 0:
                self.stdout.write(f"Preparing order {i} of {num_orders}...")

            user = random.choice(buyer_users)
            # Ensure the user has a default address, or pick one
            user_addresses = user.addresses.all()
            if not user_addresses.exists():
                self.stdout.write(self.style.WARNING(f"User {user.username} has no addresses, cannot create order. Skipping."))
                continue # Skip if no address
            
            shipping_address = user_addresses.filter(is_default_shipping=True).first() or user_addresses.first()
            billing_address = user_addresses.filter(is_default_billing=True).first() or user_addresses.first()

            order_status = random.choice(possible_order_statuses)
            order_date = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.get_current_timezone())

            order_data = {
                "user": user,
                "shipping_address_snapshot": f"{shipping_address.street_address}, {shipping_address.city}, {shipping_address.postal_code}", # Simplified snapshot
                "billing_address_snapshot": f"{billing_address.street_address}, {billing_address.city}, {billing_address.postal_code}", # Simplified snapshot
                "status": order_status,
                "total_amount": 0, # Will be calculated from items
                "payment_method": random.choice(['credit_card', 'paypal', 'bank_transfer', 'cash_on_delivery']),
                "shipping_method": random.choice(['standard', 'express']),
                "created_at": order_date,
                "updated_at": order_date if order_status == 'pending' else fake.date_time_between(start_date=order_date, end_date="now", tzinfo=timezone.get_current_timezone()),
            }
            # Order model might have more fields like discount, tax etc. This is a basic setup.
            order = Order(**order_data) # Create instance, don't save yet if using bulk_create later

            current_order_items = []
            order_total_amount = 0
            num_order_items = random.randint(1, 7)
            products_for_order = random.sample(all_products, k=min(num_order_items, len(all_products)))

            for product in products_for_order:
                if product.stock_quantity > 0:
                    quantity = random.randint(1, min(3, product.stock_quantity))
                    price_at_purchase = product.price # Assuming price doesn't change for this script
                    
                    # Decrement stock (if Order model doesn't handle this via signals)
                    # For bulk_create, this needs to be handled carefully or post-creation.
                    # Product.objects.filter(id=product.id).update(stock_quantity=F('stock_quantity') - quantity)
                    
                    item_total = price_at_purchase * quantity
                    order_total_amount += item_total
                    
                    current_order_items.append(OrderItem(
                        order=order, # This will be set after order is saved if using bulk_create for orders first
                        product=product,
                        quantity=quantity,
                        price_at_purchase=price_at_purchase
                    ))
            
            if not current_order_items: # Skip order if no items could be added
                continue

            order.total_amount = round(order_total_amount, 2)
            orders_to_create.append(order)
            # order_items_to_create.extend(current_order_items) # This needs order_id, so handle after orders are created

        # Bulk create Orders
        # If Order model has pre_save/post_save signals that are critical (e.g. generating order_id),
        # then individual .save() or smaller batches might be necessary.
        # For now, using bulk_create.
        created_orders = Order.objects.bulk_create(orders_to_create)
        self.stdout.write(self.style.SUCCESS(f'Successfully created {len(created_orders)} orders in memory.'))
        
        # Now create OrderItems, linking them to the created_orders
        # This requires re-fetching orders or matching them if bulk_create doesn't return them in a predictable way with IDs.
        # A safer way is to save orders one by one or in small batches and then their items.
        # For simplicity, let's assume we re-iterate what we prepared.
        # This is NOT the most efficient way for bulk.
        
        final_order_items_to_create = []
        order_idx = 0
        # This assumes orders_to_create and created_orders are in the same order.
        # bulk_create (on some DBs like PostgreSQL, with pk specified) returns objects with IDs.
        # Let's assume created_orders has IDs.

        # Rebuilding order_items_to_create with actual order_ids
        # This is a bit convoluted due to the way items were prepared before order PKs were known.
        # A cleaner way:
        # 1. Prepare all order data (without saving)
        # 2. Prepare all order item data (without saving, placeholder for order reference)
        # 3. Loop: order.save(), then for item in items_for_this_order: item.order = order; item.save()
        # Or: Order.objects.bulk_create(order_instances)
        # Then: Retrieve those orders (e.g., by a unique temp ID if set, or filter by users/dates)
        # Then: item.order_id = retrieved_order.id; OrderItem.objects.bulk_create(item_instances)

        # For now, let's try a simplified linking assuming order of 'created_orders' matches 'orders_to_create'
        # This is fragile. A better way is to not use bulk_create for orders if items depend on their PKs immediately.
        
        # Let's try saving orders individually to get PKs for items. This is safer.
        Order.objects.all().delete() # Clear any previously bulk_created orders for this run
        OrderItem.objects.all().delete() # Clear previous items

        order_item_count = 0
        final_orders_created_count = 0
        for user in buyer_users: # Iterate through users to ensure orders are distributed
            if final_orders_created_count >= num_orders:
                break

            num_orders_for_user = random.randint(0, 3) # Max 3 orders per user to spread them out
            for _ in range(num_orders_for_user):
                if final_orders_created_count >= num_orders:
                    break
                
                user_addresses = user.addresses.all()
                if not user_addresses.exists(): continue
                shipping_address = user_addresses.filter(is_default_shipping=True).first() or user_addresses.first()
                billing_address = user_addresses.filter(is_default_billing=True).first() or user_addresses.first()
                order_status = random.choice(possible_order_statuses)
                order_date = fake.date_time_between(start_date="-2y", end_date="now", tzinfo=timezone.get_current_timezone())

                order = Order.objects.create(
                    user=user,
                    shipping_address_snapshot=f"{shipping_address.street_address}, {shipping_address.city}",
                    billing_address_snapshot=f"{billing_address.street_address}, {billing_address.city}",
                    status=order_status,
                    total_amount=0, # Will update
                    payment_method=random.choice(['credit_card', 'paypal', 'bank_transfer', 'cash_on_delivery']),
                    shipping_method=random.choice(['standard', 'express']),
                    created_at=order_date,
                    updated_at=order_date if order_status == 'pending' else fake.date_time_between(start_date=order_date, end_date="now", tzinfo=timezone.get_current_timezone())
                )
                final_orders_created_count += 1
                
                current_order_total = 0
                items_for_this_order_instances = []
                num_items_in_order = random.randint(1, 7)
                products_for_this_order = random.sample(all_products, k=min(num_items_in_order, len(all_products)))

                for product in products_for_this_order:
                    if product.stock_quantity > 0:
                        quantity = random.randint(1, min(3, product.stock_quantity))
                        price = product.price
                        current_order_total += (price * quantity)
                        items_for_this_order_instances.append(OrderItem(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price_at_purchase=price
                        ))
                
                if items_for_this_order_instances:
                    OrderItem.objects.bulk_create(items_for_this_order_instances)
                    order_item_count += len(items_for_this_order_instances)
                    order.total_amount = round(current_order_total, 2)
                    order.save()
                else:
                    # If no items, delete the order to avoid confusion
                    order.delete()
                    final_orders_created_count -=1


        self.stdout.write(self.style.SUCCESS(f'Successfully created {final_orders_created_count} orders and {order_item_count} order items.'))
        self.stdout.write(self.style.SUCCESS('Successfully populated order-related data.'))
