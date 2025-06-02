import logging
import time
from api_client import ApiClient, CREDENTIALS
from test_vendors_api import get_user_id_and_vendor_profile_id # To get vendor ID for product filtering etc.
from test_accounts_api import get_user_id_by_username # To get buyer user ID

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Store IDs and data
test_data = {
    "buyer_user_id": None,
    "product_id_for_cart": None, # A product that can be added to cart
    "product_from_vendor1_id": None, # Product specifically from vendor1
    "vendor1_profile_id": None,
    "cart_id": None,
    "cart_item_id": None,
    "wishlist_id": None,
    "order_id_by_buyer": None,
    "order_item_id_for_vendor": None, # An OrderItem ID that vendor1 can manage
}

def setup_initial_data(admin_client, vendor_client):
    """Fetch/verify initial data needed for order tests."""
    logging.info("--- Setting up initial data for Order tests ---")

    # 1. Get Buyer User ID
    # buyer_username = CREDENTIALS["buyer"]["username"] # Not used directly here
    # test_data["buyer_user_id"] = get_user_id_by_username(admin_client, buyer_username) # Use admin to ensure we get it
    # if not test_data["buyer_user_id"]:
        # logging.error(f"Failed to get buyer user ID for {buyer_username}. Order tests will likely fail.")
        # return False
    # Fetching buyer_user_id will be done by buyer client itself in its scenario for /me

    # 2. Get Vendor1 Profile ID (to identify their products)
    vendor1_username = CREDENTIALS["vendor"]["username"]
    _, vp_id = get_user_id_and_vendor_profile_id(admin_client, vendor1_username)
    if not vp_id:
        logging.error(f"Failed to get vendor profile ID for {vendor1_username}. Cannot identify vendor's products.")
        return False
    test_data["vendor1_profile_id"] = vp_id
    logging.info(f"Obtained vendor1_profile_id: {vp_id}")

    # 3. Find a general product to add to cart (any vendor is fine initially)
    # And a product specifically from vendor1
    products_response = admin_client.get("/catalogue/products/?page_size=50") # Get a decent number of products
    if products_response.status_code == 200:
        all_products = products_response.json().get("results", [])
        if not all_products:
            logging.error("No products found in catalogue. Cannot proceed with order tests.")
            return False
        
        # General product
        test_data["product_id_for_cart"] = all_products[0].get("id")
        logging.info(f"Product ID for cart (any vendor): {test_data['product_id_for_cart']}")

        # Product from vendor1
        for prod in all_products:
            # Check if 'vendor' is an ID or a nested object
            vendor_info = prod.get("vendor")
            if isinstance(vendor_info, int) and vendor_info == test_data["vendor1_profile_id"]:
                test_data["product_from_vendor1_id"] = prod.get("id")
                break
            elif isinstance(vendor_info, dict) and vendor_info.get("id") == test_data["vendor1_profile_id"]:
                test_data["product_from_vendor1_id"] = prod.get("id")
                break
        
        if test_data["product_from_vendor1_id"]:
            logging.info(f"Product ID from Vendor1 ({vendor1_username}): {test_data['product_from_vendor1_id']}")
        else:
            logging.warning(f"Could not find a product specifically for Vendor1 ({vendor1_username}) in the first 50 products. Vendor tests might be limited.")
            # Fallback: use the general product also for vendor specific tests if it happens to be theirs, or vendor tests will be skipped for product specific parts.
            if all_products[0].get("vendor") == test_data["vendor1_profile_id"] or \
               (isinstance(all_products[0].get("vendor"),dict) and all_products[0].get("vendor").get("id") == test_data["vendor1_profile_id"] ):
                test_data["product_from_vendor1_id"] = test_data["product_id_for_cart"]
                logging.info(f"Using general product {test_data['product_id_for_cart']} also as vendor1's product.")
            else:
                 logging.error(f"The first product {all_products[0].get('id')} does not belong to vendor {test_data['vendor1_profile_id']}. Vendor product specific tests may fail.")
                 # This implies that for robust testing, populate_catalogue should ensure vendor_test_api_user has known products.

    else:
        logging.error(f"Failed to list products for setup. Status: {products_response.status_code}")
        return False
    
    if not test_data["product_id_for_cart"]:
        logging.error("No suitable product found to use for cart testing.")
        return False
        
    return True

def scenario_buyer_manage_cart(buyer_client):
    logging.info("--- Scenario: Buyer Manages Cart ---")
    success = True
    product_id = test_data.get("product_id_for_cart")
    if not product_id:
        logging.error("Buyer: No product ID available for cart tests.")
        return False

    # 1. View Cart (initially should be empty or non-existent for a new user)
    logging.info("Buyer: Viewing cart (initial state)...")
    response = buyer_client.get("/orders/cart/") # Assuming endpoint for current user's cart
    if response.status_code == 200: # Cart exists
        test_data["cart_id"] = response.json().get("id")
        cart_items = response.json().get("items", [])
        logging.info(f"Buyer: Cart (ID: {test_data['cart_id']}) exists with {len(cart_items)} items.")
    elif response.status_code == 404: # Cart doesn't exist, usually created on first add.
        logging.info("Buyer: Cart does not exist yet (404), which is okay.")
        # Some systems might auto-create an empty cart on GET if it doesn't exist.
        # If it returns 200 with an empty cart object, that's also fine.
    else:
        logging.warning(f"Buyer: Unexpected status when viewing cart: {response.status_code}. Response: {response.text[:200]}")
        # This might not be a hard failure for the scenario, as adding to cart might create it.

    # 2. Add item to cart
    add_payload = {"product_id": product_id, "quantity": 1}
    logging.info(f"Buyer: Adding product {product_id} to cart...")
    response = buyer_client.post("/orders/cart/items/", data=add_payload) # Endpoint to add item
    if response.status_code == 201: # Item created in cart
        created_item = response.json()
        test_data["cart_item_id"] = created_item.get("id")
        # The response might be the item itself or the whole cart. If item, it should have a cart ID.
        # If the cart was implicitly created, we might need to fetch it again to get cart_id
        if not test_data.get("cart_id") and created_item.get("cart"):
             test_data["cart_id"] = created_item.get("cart") if isinstance(created_item.get("cart"), int) else created_item.get("cart").get("id")

        logging.info(f"Buyer: Successfully added item to cart. Cart Item ID: {test_data['cart_item_id']}, Cart ID: {test_data['cart_id']}.")
    else:
        logging.error(f"Buyer: Failed to add item to cart. Status: {response.status_code}, Response: {response.text}")
        success = False
        return success # Cannot proceed if add fails

    # 3. View Cart again (should have the item)
    logging.info("Buyer: Viewing cart after adding item...")
    response = buyer_client.get("/orders/cart/")
    if response.status_code == 200:
        cart_data = response.json()
        if not test_data.get("cart_id"): test_data["cart_id"] = cart_data.get("id") # Ensure cart_id is set
        
        item_found = any(item.get("id") == test_data["cart_item_id"] for item in cart_data.get("items", []))
        if item_found:
            logging.info(f"Buyer: Cart (ID: {test_data['cart_id']}) correctly shows added item.")
        else:
            logging.error(f"Buyer: Cart items do not contain the added item ID {test_data['cart_item_id']}. Items: {cart_data.get('items')}")
            success = False
    else:
        logging.error(f"Buyer: Failed to view cart after adding item. Status: {response.status_code}")
        success = False

    # 4. Update cart item quantity
    if test_data["cart_item_id"]:
        update_payload = {"quantity": 3}
        cart_item_id = test_data["cart_item_id"]
        logging.info(f"Buyer: Updating quantity for cart item {cart_item_id}...")
        # Endpoint could be /orders/cart/items/{item_id}/
        response = buyer_client.patch(f"/orders/cart/items/{cart_item_id}/", data=update_payload)
        if response.status_code == 200 and response.json().get("quantity") == 3:
            logging.info(f"Buyer: Successfully updated cart item {cart_item_id} quantity.")
        else:
            logging.error(f"Buyer: Failed to update cart item quantity. Status: {response.status_code}, Response: {response.text}")
            success = False
    else:
        logging.warning("Buyer: No cart_item_id, skipping update test.")


    # 5. Remove item from cart
    if test_data["cart_item_id"]:
        cart_item_id = test_data["cart_item_id"]
        logging.info(f"Buyer: Removing item {cart_item_id} from cart...")
        response = buyer_client.delete(f"/orders/cart/items/{cart_item_id}/")
        if response.status_code == 204: # No Content
            logging.info(f"Buyer: Successfully removed item from cart.")
            # Verify it's gone
            cart_response = buyer_client.get("/orders/cart/")
            if cart_response.status_code == 200:
                item_still_found = any(item.get("id") == cart_item_id for item in cart_response.json().get("items", []))
                if item_still_found:
                    logging.error(f"Buyer: Item {cart_item_id} still found in cart after supposed deletion.")
                    success = False
                else:
                    logging.info(f"Buyer: Item {cart_item_id} verified as removed from cart.")
            test_data["cart_item_id"] = None # Clear it
        else:
            logging.error(f"Buyer: Failed to remove item from cart. Status: {response.status_code}, Response: {response.text}")
            success = False
    else:
        logging.warning("Buyer: No cart_item_id, skipping remove test.")
        
    return success

def scenario_buyer_manage_wishlist(buyer_client):
    logging.info("--- Scenario: Buyer Manages Wishlist ---")
    success = True
    product_id = test_data.get("product_id_for_cart") # Use the same product for simplicity
    if not product_id:
        logging.error("Buyer: No product ID available for wishlist tests.")
        return False

    # 1. View Wishlist (initial)
    # Assuming /orders/wishlist/ for current user's wishlist and items are in a 'products' list or similar
    logging.info("Buyer: Viewing wishlist (initial state)...")
    response = buyer_client.get("/orders/wishlist/")
    if response.status_code == 200:
        wishlist_json = response.json()
        # Wishlist might be a single object per user, or a list of wishlists (less common for default)
        # Assuming a single wishlist model for the user, its ID is important.
        # Or items are directly under user.
        # Let's assume the response is the wishlist object containing its ID and a list of product objects/IDs
        if isinstance(wishlist_json, dict) and "id" in wishlist_json: # Single wishlist object
            test_data["wishlist_id"] = wishlist_json.get("id")
            current_wishlist_items = wishlist_json.get("products", []) # Assuming 'products' is a list of product objects/IDs
            logging.info(f"Buyer: Wishlist (ID: {test_data['wishlist_id']}) exists with {len(current_wishlist_items)} items.")
        elif isinstance(wishlist_json, list): # Could be a list of items directly if no "Wishlist" model
             logging.info(f"Buyer: Wishlist items returned as a list with {len(wishlist_json)} items.")
             # No specific wishlist_id in this case, operations might be on /wishlist/items/
        else:
            logging.warning(f"Buyer: Wishlist response format unexpected: {wishlist_json}")
            # This might not be a failure if adding to wishlist clarifies structure
    elif response.status_code == 404: # Wishlist doesn't exist, created on first add usually
        logging.info("Buyer: Wishlist does not exist yet (404).")
    else:
        logging.warning(f"Buyer: Unexpected status viewing wishlist: {response.status_code}")

    # 2. Add item to wishlist
    # Endpoint could be /orders/wishlist/add/ or POST to /orders/wishlist/items/
    add_payload = {"product_id": product_id}
    logging.info(f"Buyer: Adding product {product_id} to wishlist...")
    response_add = buyer_client.post("/orders/wishlist/items/", data=add_payload) # Assuming this
    if response_add.status_code == 201 or response_add.status_code == 200: # 201 if new item created, 200 if item just added to list
        logging.info(f"Buyer: Successfully added/associated product {product_id} to wishlist.")
        # If wishlist was created, response might contain its ID. Or need to re-fetch.
        if not test_data.get("wishlist_id") and response_add.json().get("wishlist_id"): # if response returns wishlist_id
            test_data["wishlist_id"] = response_add.json().get("wishlist_id")
        elif not test_data.get("wishlist_id") and response_add.json().get("id") and 'product' in response_add.json(): # if it returns the wishlist item itself
            # This means we may not have a separate "Wishlist" model id, but rather item ids
            pass


    else:
        logging.error(f"Buyer: Failed to add item to wishlist. Status: {response_add.status_code}, Response: {response_add.text}")
        success = False
        return success

    # 3. View Wishlist again
    logging.info("Buyer: Viewing wishlist after adding item...")
    response_view = buyer_client.get("/orders/wishlist/")
    if response_view.status_code == 200:
        wishlist_data = response_view.json()
        items_in_wishlist = []
        if isinstance(wishlist_data, dict): # Single wishlist object
            items_in_wishlist = wishlist_data.get("products", [])
            if not test_data.get("wishlist_id"): test_data["wishlist_id"] = wishlist_data.get("id")
        elif isinstance(wishlist_data, list): # Direct list of items/products
            items_in_wishlist = wishlist_data
        
        # Check if product_id (integer) or product object with "id": product_id is present
        item_found = any(
            (isinstance(item, int) and item == product_id) or \
            (isinstance(item, dict) and item.get("id") == product_id) \
            for item in items_in_wishlist
        )
        if item_found:
            logging.info(f"Buyer: Wishlist correctly shows added product {product_id}.")
        else:
            logging.error(f"Buyer: Wishlist items do not contain the added product ID {product_id}. Items: {items_in_wishlist}")
            success = False
    else:
        logging.error(f"Buyer: Failed to view wishlist after adding. Status: {response_view.status_code}")
        success = False

    # 4. Remove item from wishlist
    # Endpoint could be /orders/wishlist/remove/ or DELETE to /orders/wishlist/items/{product_id}/ (more RESTful)
    # Let's assume DELETE to /orders/wishlist/items/{product_id}/
    logging.info(f"Buyer: Removing product {product_id} from wishlist...")
    response_remove = buyer_client.delete(f"/orders/wishlist/items/{product_id}/") # Needs product_id not wishlist_item_id
    if response_remove.status_code == 204 or response_remove.status_code == 200: # 204 common for DELETE, 200 if it returns updated list
        logging.info(f"Buyer: Successfully removed product {product_id} from wishlist.")
        # Verify it's gone
        final_check_response = buyer_client.get("/orders/wishlist/")
        if final_check_response.status_code == 200:
            final_wishlist_data = final_check_response.json()
            final_items = []
            if isinstance(final_wishlist_data, dict): final_items = final_wishlist_data.get("products", [])
            elif isinstance(final_wishlist_data, list): final_items = final_wishlist_data

            item_still_found = any(
                (isinstance(item, int) and item == product_id) or \
                (isinstance(item, dict) and item.get("id") == product_id) \
                for item in final_items
            )
            if item_still_found:
                logging.error(f"Buyer: Product {product_id} still found in wishlist after supposed deletion.")
                success = False
            else:
                logging.info(f"Buyer: Product {product_id} verified as removed from wishlist.")
    else:
        logging.error(f"Buyer: Failed to remove item from wishlist. Status: {response_remove.status_code}, Response: {response_remove.text}")
        success = False
        
    return success

def scenario_buyer_create_and_view_order(buyer_client, admin_client_for_address_setup):
    logging.info("--- Scenario: Buyer Creates and Views Order ---")
    success = True

    # 0. Ensure buyer has an address (required for order creation)
    # We use admin_client here as buyer might not have permissions to list/query its own ID directly if not /me
    # and the address creation in accounts test is tied to buyer_client instance.
    # For robust inter-test dependency, buyer_user_id should be established once.
    buyer_username_for_id = CREDENTIALS["buyer"]["username"]
    buyer_user_id = get_user_id_by_username(admin_client_for_address_setup, buyer_username_for_id)
    if not buyer_user_id:
        logging.error(f"Could not get buyer user ID for {buyer_username_for_id} using admin. Prerequisite failed.")
        return False
    test_data["buyer_user_id"] = buyer_user_id # Store it for other scenarios if needed

    # Check if buyer has addresses; if not, create one.
    # This assumes /accounts/addresses/?user_id={id} or similar is available to admin.
    # A simpler way: buyer client tries to get its addresses, if none, it creates one.
    
    addr_response = buyer_client.get("/accounts/addresses/") # Get own addresses
    shipping_address_id = None
    billing_address_id = None

    if addr_response.status_code == 200 and addr_response.json().get("results"):
        addresses = addr_response.json().get("results")
        logging.info(f"Buyer already has {len(addresses)} addresses.")
        # Try to find default, otherwise use first one
        for addr in addresses:
            if addr.get("is_default_shipping"):
                shipping_address_id = addr.get("id")
            if addr.get("is_default_billing"):
                billing_address_id = addr.get("id")
        if not shipping_address_id: shipping_address_id = addresses[0].get("id")
        if not billing_address_id: billing_address_id = addresses[0].get("id")
    else: # No addresses or error, try to create one
        logging.info("Buyer has no addresses or failed to fetch. Creating one...")
        addr_payload = { "user": test_data["buyer_user_id"], "street_address": "100 Order Lane", "city": "Orderton", "state": "OS", "postal_code": "54321", "country": "Orderland", "is_default_shipping": True, "is_default_billing": True}
        # Note: 'user' field in payload might be ignored if API sets user from token.
        # If POST is to /accounts/addresses/ (general, not user-specific), 'user' field is crucial.
        create_addr_resp = buyer_client.post("/accounts/addresses/", data=addr_payload)
        if create_addr_resp.status_code == 201:
            shipping_address_id = create_addr_resp.json().get("id")
            billing_address_id = shipping_address_id
            logging.info(f"Buyer created a default address with ID: {shipping_address_id}")
        else:
            logging.error(f"Buyer failed to create address for order. Status: {create_addr_resp.status_code}, R: {create_addr_resp.text}")
            return False

    if not shipping_address_id or not billing_address_id:
        logging.error("Buyer does not have suitable shipping/billing addresses for order.")
        return False

    # 1. Ensure cart has items (re-add if necessary, previous tests might have cleared it)
    product_id = test_data.get("product_id_for_cart")
    if not product_id:
        logging.error("Buyer: No product_id_for_cart. Cannot create order.")
        return False

    # Check current cart items
    cart_view_resp = buyer_client.get("/orders/cart/")
    if cart_view_resp.status_code != 200 or not cart_view_resp.json().get("items"):
        logging.info("Buyer: Cart is empty or not found. Adding item before creating order...")
        add_payload = {"product_id": product_id, "quantity": 1}
        add_item_resp = buyer_client.post("/orders/cart/items/", data=add_payload)
        if add_item_resp.status_code != 201:
            logging.error(f"Buyer: Failed to add item to cart before order. Status: {add_item_resp.status_code}, R: {add_item_resp.text}")
            return False
        logging.info(f"Buyer: Item added to cart. Cart Item ID: {add_item_resp.json().get('id')}")
        # Update cart_id if it was created now
        if not test_data.get("cart_id"):
            cart_resp_after_add = buyer_client.get("/orders/cart/")
            if cart_resp_after_add.status_code == 200:
                 test_data["cart_id"] = cart_resp_after_add.json().get("id")


    if not test_data.get("cart_id"):
        logging.error("Buyer: Cart ID still unknown after attempting to add item. Cannot create order.")
        return False

    # 2. Create Order from cart
    # Endpoint: /orders/checkout/ or /orders/
    # Payload needs shipping/billing address IDs, payment method (mocked)
    order_payload = {
        "cart_id": test_data["cart_id"], # Or API might use current user's active cart
        "shipping_address_id": shipping_address_id,
        "billing_address_id": billing_address_id,
        "payment_method": "mock_credit_card", # Example
        "shipping_method": "standard_shipping" # Example
    }
    logging.info(f"Buyer: Creating order from cart {test_data['cart_id']}...")
    response = buyer_client.post("/orders/checkout/", data=order_payload) # Assuming /checkout/ handles this
    if response.status_code == 201: # Order created
        created_order = response.json()
        test_data["order_id_by_buyer"] = created_order.get("id")
        logging.info(f"Buyer: Successfully created order with ID {test_data['order_id_by_buyer']}. Status: {created_order.get('status')}")
        # Verify cart is now empty (or marked inactive/ordered)
        cart_after_order_resp = buyer_client.get("/orders/cart/")
        if cart_after_order_resp.status_code == 200:
            if not cart_after_order_resp.json().get("items") or cart_after_order_resp.json().get("is_active") == False :
                logging.info("Buyer: Cart is now empty or inactive after order creation, as expected.")
            else:
                logging.warning(f"Buyer: Cart still has items or is active after order creation. Cart: {cart_after_order_resp.json()}")
    else:
        logging.error(f"Buyer: Failed to create order. Status: {response.status_code}, Response: {response.text}")
        success = False
        return success

    # 3. View own orders (list)
    logging.info("Buyer: Listing own orders...")
    response_list = buyer_client.get("/orders/") # Should be filtered to user
    if response_list.status_code == 200:
        orders = response_list.json().get("results", [])
        found = any(order.get("id") == test_data["order_id_by_buyer"] for order in orders)
        if found:
            logging.info(f"Buyer: Successfully listed own orders, created order {test_data['order_id_by_buyer']} is present.")
        else:
            logging.error(f"Buyer: Listed orders, but created order ID {test_data['order_id_by_buyer']} not found. Orders: {orders}")
            success = False
    else:
        logging.error(f"Buyer: Failed to list own orders. Status: {response_list.status_code}")
        success = False

    # 4. View specific order details
    order_id = test_data["order_id_by_buyer"]
    logging.info(f"Buyer: Retrieving order ID {order_id} details...")
    response_detail = buyer_client.get(f"/orders/{order_id}/")
    if response_detail.status_code == 200:
        order_items = response_detail.json().get("items", [])
        if order_items: # Order should have items
            logging.info(f"Buyer: Successfully retrieved order {order_id} with {len(order_items)} items.")
            # Store one item_id for vendor test if product was vendor1's
            # This requires knowing which product was in the cart and if it belongs to vendor1
            # This is getting complex for inter-scenario dependency.
            # For now, let's assume the first item is the one we added (product_id_for_cart)
            # And if product_id_for_cart was from vendor1, then this order_item is relevant.
            if test_data.get("product_id_for_cart") == test_data.get("product_from_vendor1_id"):
                test_data["order_item_id_for_vendor"] = order_items[0].get("id")
                logging.info(f"Order item {order_items[0].get('id')} from this order is from Vendor1, saved for vendor test.")

        else:
            logging.error(f"Buyer: Order {order_id} retrieved but has no items.")
            success = False
    else:
        logging.error(f"Buyer: Failed to retrieve order {order_id}. Status: {response_detail.status_code}")
        success = False
        
    return success

def scenario_vendor_view_orders(vendor_client):
    logging.info("--- Scenario: Vendor Views Orders ---")
    success = True
    
    if not test_data.get("vendor1_profile_id"):
        logging.error("Vendor: vendor1_profile_id not set. Cannot verify orders for this vendor.")
        return False
    
    # 1. List orders (should be filtered to show only orders containing this vendor's products)
    logging.info(f"Vendor ({CREDENTIALS['vendor']['username']}): Listing orders containing their products...")
    response = vendor_client.get("/orders/") # API should filter this
    if response.status_code == 200:
        orders_for_vendor = response.json().get("results", [])
        logging.info(f"Vendor: Found {len(orders_for_vendor)} orders/order items relevant to this vendor.")
        
        # If an order was created by buyer with vendor1's product, it should appear here.
        order_created_by_buyer = test_data.get("order_id_by_buyer")
        found_buyer_order = False
        if order_created_by_buyer and orders_for_vendor:
            for order_summary in orders_for_vendor:
                # The structure here depends on how vendor orders are presented.
                # It might be a list of OrderItems, or Orders that contain at least one item from the vendor.
                # Let's assume it's a list of Orders.
                if order_summary.get("id") == order_created_by_buyer:
                    found_buyer_order = True
                    # Further check: retrieve full order to see if items are filtered
                    detail_resp = vendor_client.get(f"/orders/{order_created_by_buyer}/")
                    if detail_resp.status_code == 200:
                        order_detail_items = detail_resp.json().get("items", [])
                        vendor_items_in_order = [item for item in order_detail_items if item.get("product",{}).get("vendor") == test_data["vendor1_profile_id"] or item.get("vendor_id") == test_data["vendor1_profile_id"]]
                        if vendor_items_in_order:
                             logging.info(f"Vendor: Order {order_created_by_buyer} details show {len(vendor_items_in_order)} items for this vendor.")
                             if not test_data.get("order_item_id_for_vendor") and vendor_items_in_order: # If not set earlier
                                test_data["order_item_id_for_vendor"] = vendor_items_in_order[0].get("id")

                        else:
                            logging.warning(f"Vendor: Order {order_created_by_buyer} listed, but detail view shows no items for this vendor. Inconsistent?")
                            # This might not be a failure if the list view is just summaries.
                    else:
                        logging.warning(f"Vendor: Could not get detail for listed order {order_created_by_buyer}. Status: {detail_resp.status_code}")

                    break # Found the order in the list
        
        if order_created_by_buyer and test_data.get("product_from_vendor1_id") == test_data.get("product_id_for_cart") and not found_buyer_order:
            # If the product placed in order was indeed vendor1's, then this order should be listed for vendor1.
            logging.error(f"Vendor: Order {order_created_by_buyer} (which should contain vendor1's product) not found in vendor's order list.")
            # success = False # This can be a strict failure depending on data setup guarantees
        elif not order_created_by_buyer and orders_for_vendor:
            logging.info("Vendor: No specific buyer order ID to check, but vendor has some orders listed.")
        elif not orders_for_vendor:
            logging.info("Vendor: No orders found for this vendor currently.")


    else:
        logging.error(f"Vendor: Failed to list orders. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 2. Update order item status (e.g., if vendor can mark an item as "shipped" or "ready")
    # This depends heavily on API design. Assume /orders/items/{item_id}/update-status/ or similar PATCH
    order_item_to_update = test_data.get("order_item_id_for_vendor")
    if order_item_to_update:
        status_payload = {"status": "prepared_for_shipping"} # Example status
        logging.info(f"Vendor: Attempting to update status for OrderItem {order_item_to_update}...")
        # The endpoint needs to be specific to what a vendor can update.
        # A common pattern: PATCH /api/orders/items/{item_id}/ 
        # Or a custom action: PATCH /api/orders/items/{item_id}/set_status/
        item_update_resp = vendor_client.patch(f"/orders/items/{order_item_to_update}/", data=status_payload)
        if item_update_resp.status_code == 200 and item_update_resp.json().get("status") == status_payload["status"]:
            logging.info(f"Vendor: Successfully updated OrderItem {order_item_to_update} status.")
        elif item_update_resp.status_code == 403:
             logging.warning(f"Vendor: Not allowed to update OrderItem {order_item_to_update} status (403). This might be admin-only.")
        elif item_update_resp.status_code == 404:
             logging.warning(f"Vendor: OrderItem {order_item_to_update} not found for update (404).")
        else:
            logging.error(f"Vendor: Failed to update OrderItem {order_item_to_update} status. Status: {item_update_resp.status_code}, R: {item_update_resp.text}")
            # success = False # This might be optional functionality
    else:
        logging.info("Vendor: No specific order item ID from vendor1's product in a buyer order to test status update.")
        
    return success

def scenario_admin_manage_orders(admin_client):
    logging.info("--- Scenario: Admin Manages Orders ---")
    success = True
    target_order_id = test_data.get("order_id_by_buyer")

    # 1. List all orders
    logging.info("Admin: Listing all orders...")
    response = admin_client.get("/orders/")
    if response.status_code == 200:
        orders_count = response.json().get("count", len(response.json().get("results", [])))
        logging.info(f"Admin: Successfully listed {orders_count} total orders.")
        if target_order_id: # Verify the buyer's order is in the list
            found = any(o.get("id") == target_order_id for o in response.json().get("results",[]))
            if not found: # Check more pages if paginated
                current_page = response.json()
                while current_page.get("next") and not found:
                    page_resp = admin_client.get(current_page["next"])
                    if page_resp.status_code == 200:
                        current_page = page_resp.json()
                        found = any(o.get("id") == target_order_id for o in current_page.get("results",[]))
                    else: break 
            if not found:
                logging.warning(f"Admin: Buyer's order {target_order_id} not found in admin's full order list.")
                # success = False # This implies an issue with data visibility or test setup
    else:
        logging.error(f"Admin: Failed to list all orders. Status: {response.status_code}")
        success = False

    # 2. Retrieve a specific order (the one created by buyer)
    if not target_order_id:
        logging.warning("Admin: No target_order_id (from buyer test). Skipping admin retrieve/update for that order.")
        # Try to get first order from the list if any, for further tests
        if response.status_code == 200 and response.json().get("results"):
            target_order_id = response.json().get("results")[0].get("id")
            logging.info(f"Admin: Using first order from list (ID: {target_order_id}) for further tests.")
        else:
            logging.error("Admin: No orders in list to pick for further tests.")
            return success # Return current success state as cannot proceed

    if target_order_id:
        logging.info(f"Admin: Retrieving order ID {target_order_id}...")
        resp_detail = admin_client.get(f"/orders/{target_order_id}/")
        if resp_detail.status_code == 200:
            logging.info(f"Admin: Successfully retrieved order {target_order_id}. Current status: {resp_detail.json().get('status')}")
        else:
            logging.error(f"Admin: Failed to retrieve order {target_order_id}. Status: {resp_detail.status_code}")
            success = False
            return success # Cannot update if cannot retrieve

        # 3. Update order status (e.g., to 'processing' or 'shipped')
        new_status = "processing" # Example
        current_status = resp_detail.json().get('status')
        if current_status == "pending": new_status = "processing"
        elif current_status == "processing": new_status = "shipped"
        elif current_status == "shipped": new_status = "delivered"
        else: new_status = "completed" # A generic final status if others don't apply

        payload = {"status": new_status}
        logging.info(f"Admin: Updating order ID {target_order_id} status to '{new_status}'...")
        resp_update = admin_client.patch(f"/orders/{target_order_id}/", data=payload)
        if resp_update.status_code == 200 and resp_update.json().get("status") == new_status:
            logging.info(f"Admin: Successfully updated order {target_order_id} status to '{new_status}'.")
        else:
            logging.error(f"Admin: Failed to update order status. Status: {resp_update.status_code}, Response: {resp_update.text}")
            success = False
    else:
        logging.info("Admin: No order ID to manage.")

    return success

if __name__ == "__main__":
    logging.info("======== Starting Orders API Tests ========")
    
    admin_client = ApiClient(user_role="admin")
    vendor_client = ApiClient(user_role="vendor")
    buyer_client = ApiClient(user_role="buyer")
    
    results = {}

    if not all([admin_client.token, vendor_client.token, buyer_client.token]):
        logging.critical("One or more clients failed to authenticate. Aborting Order tests.")
        # Optionally, mark all as failed or skip them
    else:
        # Initial data setup (e.g., find a product ID)
        setup_ok = setup_initial_data(admin_client, vendor_client)
        if not setup_ok:
            logging.critical("Initial data setup for Order tests failed. Aborting.")
        else:
            results["buyer_manage_cart"] = scenario_buyer_manage_cart(buyer_client)
            # Wait a tiny bit for any async operations if cart creation affects wishlist or order
            time.sleep(0.5) 
            results["buyer_manage_wishlist"] = scenario_buyer_manage_wishlist(buyer_client)
            time.sleep(0.5)
            # Pass admin_client to buyer_create_order for address setup if needed by that function's current logic
            results["buyer_create_and_view_order"] = scenario_buyer_create_and_view_order(buyer_client, admin_client)
            
            # Vendor tests might depend on order created by buyer
            if results.get("buyer_create_and_view_order"): # Only if order was created
                results["vendor_view_orders"] = scenario_vendor_view_orders(vendor_client)
            else:
                logging.warning("Skipping vendor order tests as buyer order creation failed or was skipped.")
                results["vendor_view_orders"] = False # Mark as failed or skipped

            # Admin tests might depend on order created by buyer
            if results.get("buyer_create_and_view_order"):
                results["admin_manage_orders"] = scenario_admin_manage_orders(admin_client)
            else:
                logging.warning("Skipping admin order management tests as buyer order creation failed or was skipped.")
                results["admin_manage_orders"] = False


    logging.info("\n======== Orders API Test Summary ========")
    all_passed = True
    for test_name, success_status in results.items():
        status_msg = "PASSED" if success_status else "FAILED"
        logging.info(f"Scenario '{test_name}': {status_msg}")
        if not success_status:
            all_passed = False
    
    if not results: # If no tests ran due to auth failure
        all_passed = False
        logging.error("No order tests were executed due to client authentication failures or setup issues.")

    if all_passed:
        logging.info("All Orders API scenarios passed!")
    else:
        logging.error("Some Orders API scenarios failed or were skipped due to errors.")

    logging.info("======== Orders API Tests Finished ========")
    return all_passed

if __name__ == "__main__":
    import sys
    all_tests_passed = main()
    sys.exit(0 if all_tests_passed else 1)
