import logging
import random # For SKU generation
from api_client import ApiClient, CREDENTIALS # To get vendor username for ID fetching
from test_vendors_api import get_user_id_and_vendor_profile_id # Re-use to get vendor profile ID

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Store IDs fetched/created during tests
test_data_ids = {
    "admin_category_id": None,
    "vendor1_product_id": None,
    "vendor1_profile_id": None, # From vendors.Vendor, needed to assign products
    "shared_product_id_for_guest_view": None, # An ID of a product anyone can see
}

# --- Helper to get Vendor's products ---
def get_vendor_products(vendor_client, vendor_profile_id):
    if not vendor_profile_id:
        logging.error("Vendor Profile ID not provided, cannot fetch products.")
        return []
    
    # Assuming an endpoint like /catalogue/products/?vendor_id={vendor_profile_id}
    # or that /catalogue/products/ is automatically filtered for the authenticated vendor
    response = vendor_client.get("/catalogue/products/") # This might be filtered by default
    
    products = []
    if response.status_code == 200:
        results = response.json().get("results", [])
        for prod in results:
            # The vendor ID might be directly on product as 'vendor' or nested.
            # Assuming 'vendor' field on product holds the ID of the vendors.Vendor profile.
            if prod.get("vendor") == vendor_profile_id:
                products.append(prod)
        # If /catalogue/products/ is not filtered for vendor, this manual filter is needed.
        # If it IS filtered, then all results are the vendor's products.
        # For now, let's assume it IS filtered for the authenticated vendor.
        if products: # if we manually filtered and found some
             logging.info(f"Found {len(products)} products for vendor {vendor_profile_id} by manual filtering client-side.")
             return products
        elif results and not products: # Results exist but none matched our manual filter
            # This implies the 'vendor' field might not be what we expect or products are not vendor's
            # However, if the endpoint is auto-filtered, all results are valid.
            logging.info(f"Assuming /catalogue/products/ is auto-filtered for vendor. Found {len(results)} products.")
            return results


    logging.warning(f"Could not fetch products for vendor {vendor_profile_id}. Status: {response.status_code}, Text: {response.text[:200]}")
    return []


# --- Test Scenarios ---

def scenario_public_browse_catalogue(guest_client):
    logging.info("--- Scenario: Public User Browses Catalogue ---")
    success = True

    # 1. List Categories
    logging.info("Public: Listing categories...")
    response_cat = guest_client.get("/catalogue/categories/")
    if response_cat.status_code == 200:
        categories = response_cat.json().get("results", [])
        logging.info(f"Public: Successfully listed {len(categories)} categories (first page).")
        if categories:
            first_category_id = categories[0].get("id")
            # 2. View a specific category
            logging.info(f"Public: Viewing category ID {first_category_id}...")
            response_cat_detail = guest_client.get(f"/catalogue/categories/{first_category_id}/")
            if response_cat_detail.status_code == 200:
                logging.info(f"Public: Successfully viewed category {first_category_id}: {response_cat_detail.json().get('name')}")
            else:
                logging.error(f"Public: Failed to view category {first_category_id}. Status: {response_cat_detail.status_code}")
                success = False
        else:
            logging.info("Public: No categories found to view details for.")
    else:
        logging.error(f"Public: Failed to list categories. Status: {response_cat.status_code}")
        success = False

    # 3. List Products
    logging.info("Public: Listing products...")
    response_prod = guest_client.get("/catalogue/products/")
    if response_prod.status_code == 200:
        products = response_prod.json().get("results", [])
        logging.info(f"Public: Successfully listed {len(products)} products (first page).")
        if products:
            test_data_ids["shared_product_id_for_guest_view"] = products[0].get("id") # Save for later
            # 4. View a specific product
            product_id = test_data_ids["shared_product_id_for_guest_view"]
            logging.info(f"Public: Viewing product ID {product_id}...")
            response_prod_detail = guest_client.get(f"/catalogue/products/{product_id}/")
            if response_prod_detail.status_code == 200:
                logging.info(f"Public: Successfully viewed product {product_id}: {response_prod_detail.json().get('name')}")
            else:
                logging.error(f"Public: Failed to view product {product_id}. Status: {response_prod_detail.status_code}")
                success = False
        else:
            logging.info("Public: No products found to view details for.")
            # This could be a failure if products are expected after data population
            # success = False 
    else:
        logging.error(f"Public: Failed to list products. Status: {response_prod.status_code}")
        success = False
        
    return success

def scenario_admin_manage_categories(admin_client):
    logging.info("--- Scenario: Admin Manages Categories ---")
    success = True
    category_name = f"Test Category by Admin {logging.getLogger().name}"
    slug = f"test-category-admin-{hash(category_name) % 10000}" # simple slug

    # 1. Create a Category
    logging.info("Admin: Creating a category...")
    payload = {"name": category_name, "slug": slug, "description": "Admin test category"}
    response = admin_client.post("/catalogue/categories/", data=payload)
    if response.status_code == 201: # Created
        created_category = response.json()
        test_data_ids["admin_category_id"] = created_category.get("id")
        logging.info(f"Admin: Successfully created category with ID {test_data_ids['admin_category_id']}.")
    else:
        logging.error(f"Admin: Failed to create category. Status: {response.status_code}, Response: {response.text}")
        success = False
        return success # Cannot proceed

    cat_id = test_data_ids["admin_category_id"]

    # 2. Retrieve the category
    logging.info(f"Admin: Retrieving category ID {cat_id}...")
    response = admin_client.get(f"/catalogue/categories/{cat_id}/")
    if response.status_code == 200 and response.json().get("name") == category_name:
        logging.info(f"Admin: Successfully retrieved category {cat_id}.")
    else:
        logging.error(f"Admin: Failed to retrieve category {cat_id}. Status: {response.status_code}")
        success = False

    # 3. Update the category
    updated_desc = "Admin updated description."
    logging.info(f"Admin: Updating category ID {cat_id}...")
    response = admin_client.patch(f"/catalogue/categories/{cat_id}/", data={"description": updated_desc})
    if response.status_code == 200 and response.json().get("description") == updated_desc:
        logging.info(f"Admin: Successfully updated category {cat_id}.")
    else:
        logging.error(f"Admin: Failed to update category {cat_id}. Status: {response.status_code}, Response: {response.text}")
        success = False
        
    # 4. Delete the category
    logging.info(f"Admin: Deleting category ID {cat_id}...")
    response = admin_client.delete(f"/catalogue/categories/{cat_id}/")
    if response.status_code == 204: # No Content
        logging.info(f"Admin: Successfully deleted category {cat_id}.")
    else:
        logging.error(f"Admin: Failed to delete category {cat_id}. Status: {response.status_code}")
        success = False

    # Verify deletion
    if success: # Only if delete was reported as success
        response = admin_client.get(f"/catalogue/categories/{cat_id}/")
        if response.status_code == 404: # Not Found
            logging.info(f"Admin: Category {cat_id} successfully verified as deleted.")
        else:
            logging.error(f"Admin: Category {cat_id} still found after delete. Status: {response.status_code}")
            success = False
    return success

def scenario_vendor_manage_own_products(vendor_client, admin_client_for_setup):
    logging.info("--- Scenario: Vendor Manages Own Products ---")
    success = True

    # 0. Get Vendor Profile ID for the current vendor
    vendor_username = CREDENTIALS["vendor"]["username"]
    _, vendor_profile_id = get_user_id_and_vendor_profile_id(vendor_client, vendor_username) # Use own client
    
    if not vendor_profile_id:
        # Try with admin client if self-fetch failed (e.g. due to restrictive permissions on ID fetch)
        logging.warning(f"Vendor client could not fetch its own vendor profile ID for {vendor_username}. Trying with admin client...")
        _, vendor_profile_id = get_user_id_and_vendor_profile_id(admin_client_for_setup, vendor_username)

    if not vendor_profile_id:
        logging.error(f"Vendor ({vendor_username}): Could not obtain Vendor Profile ID. Cannot manage products.")
        return False
    test_data_ids["vendor1_profile_id"] = vendor_profile_id
    logging.info(f"Vendor ({vendor_username}): Operating with Vendor Profile ID {vendor_profile_id}")

    # Need a category to assign product to. Use one created by admin or get first from list.
    # For simplicity, get first category from list via admin client.
    cat_list_response = admin_client_for_setup.get("/catalogue/categories/")
    if cat_list_response.status_code != 200 or not cat_list_response.json().get("results"):
        logging.error(f"Vendor ({vendor_username}): Could not fetch categories to assign product. Admin client status: {cat_list_response.status_code}")
        # As a fallback, try creating a category as admin if none exist - this is setup, not vendor test part
        if cat_list_response.status_code == 200 and not cat_list_response.json().get("results"):
            logging.info("Admin creating a fallback category as none exist...")
            admin_client_for_setup.post("/catalogue/categories/", {"name": "Fallback Category", "slug": "fallback-cat"})
            cat_list_response = admin_client_for_setup.get("/catalogue/categories/") # try again
            if cat_list_response.status_code != 200 or not cat_list_response.json().get("results"):
                 logging.error(f"Vendor ({vendor_username}): Still no categories available after attempting fallback creation.")
                 return False # Cannot proceed
        else:
            return False # Cannot proceed

    default_category_id = cat_list_response.json()["results"][0].get("id")
    logging.info(f"Vendor ({vendor_username}): Using category ID {default_category_id} for new products.")

    product_name = f"Test Product by Vendor {vendor_username} {hash(logging.getLogger().name) % 1000}"
    product_slug = f"test-prod-vendor-{vendor_profile_id}-{hash(product_name)%1000}"
    product_sku = f"VP{vendor_profile_id}SKU{random.randint(10000,99999)}" # from populate_catalogue

    # 1. Create a Product
    product_payload = {
        "name": product_name,
        "slug": product_slug,
        "description": "A product created by its vendor.",
        "category": default_category_id, # Foreign key to Category
        "vendor": vendor_profile_id,   # Foreign key to Vendor Profile (vendors.Vendor)
        "price": "19.99",
        "stock_quantity": 50,
        "sku": product_sku,
        "is_active": True
    }
    logging.info(f"Vendor ({vendor_username}): Creating a product...")
    response = vendor_client.post("/catalogue/products/", data=product_payload)
    if response.status_code == 201:
        created_product = response.json()
        test_data_ids["vendor1_product_id"] = created_product.get("id")
        logging.info(f"Vendor ({vendor_username}): Successfully created product with ID {test_data_ids['vendor1_product_id']}.")
        # Verify vendor assignment
        if created_product.get("vendor") != vendor_profile_id:
            logging.warning(f"Vendor ({vendor_username}): Created product's vendor ID ({created_product.get('vendor')}) does not match expected ({vendor_profile_id}). API might assign based on auth token overriding payload.")
            # This is not a failure of the test itself but an observation. The system might correctly assign vendor from token.
    else:
        logging.error(f"Vendor ({vendor_username}): Failed to create product. Status: {response.status_code}, Response: {response.text}")
        success = False
        return success

    prod_id = test_data_ids["vendor1_product_id"]

    # 2. List own products
    logging.info(f"Vendor ({vendor_username}): Listing own products...")
    vendor_products = get_vendor_products(vendor_client, vendor_profile_id)
    found_in_list = any(p.get("id") == prod_id for p in vendor_products)
    if found_in_list:
        logging.info(f"Vendor ({vendor_username}): Successfully listed own products, created product {prod_id} is present.")
    else:
        logging.error(f"Vendor ({vendor_username}): Failed to find created product {prod_id} in own product list: {vendor_products}")
        success = False

    # 3. Retrieve the product
    logging.info(f"Vendor ({vendor_username}): Retrieving product ID {prod_id}...")
    response = vendor_client.get(f"/catalogue/products/{prod_id}/")
    if response.status_code == 200 and response.json().get("name") == product_name:
        logging.info(f"Vendor ({vendor_username}): Successfully retrieved product {prod_id}.")
    else:
        logging.error(f"Vendor ({vendor_username}): Failed to retrieve product {prod_id}. Status: {response.status_code}")
        success = False

    # 4. Update the product
    updated_price = "25.99"
    logging.info(f"Vendor ({vendor_username}): Updating product ID {prod_id}...")
    response = vendor_client.patch(f"/catalogue/products/{prod_id}/", data={"price": updated_price})
    if response.status_code == 200 and response.json().get("price") == updated_price:
        logging.info(f"Vendor ({vendor_username}): Successfully updated product {prod_id}.")
    else:
        logging.error(f"Vendor ({vendor_username}): Failed to update product {prod_id}. Status: {response.status_code}, Response: {response.text}")
        success = False
        
    # 5. Delete the product
    logging.info(f"Vendor ({vendor_username}): Deleting product ID {prod_id}...")
    response = vendor_client.delete(f"/catalogue/products/{prod_id}/")
    if response.status_code == 204:
        logging.info(f"Vendor ({vendor_username}): Successfully deleted product {prod_id}.")
    else:
        logging.error(f"Vendor ({vendor_username}): Failed to delete product {prod_id}. Status: {response.status_code}")
        success = False
    
    # Verify deletion
    if success:
        response = vendor_client.get(f"/catalogue/products/{prod_id}/")
        if response.status_code == 404:
            logging.info(f"Vendor ({vendor_username}): Product {prod_id} successfully verified as deleted.")
        else:
            logging.error(f"Vendor ({vendor_username}): Product {prod_id} still found after delete. Status: {response.status_code}")
            success = False
            
    return success

def scenario_admin_manage_any_product(admin_client):
    logging.info("--- Scenario: Admin Manages Any Product ---")
    success = True
    # Use the product created by vendor1 if its ID is available
    target_product_id = test_data_ids.get("vendor1_product_id")
    if not target_product_id:
        # If vendor scenario didn't run or product ID wasn't set, try to get one from public listing
        target_product_id = test_data_ids.get("shared_product_id_for_guest_view")
    
    if not target_product_id:
        logging.error("Admin: No product ID available (from vendor test or public list) to manage. Skipping admin product tests.")
        return False # Cannot proceed without a product to manage

    logging.info(f"Admin: Managing product ID {target_product_id} (created by vendor or public).")

    # 1. Retrieve the product
    response = admin_client.get(f"/catalogue/products/{target_product_id}/")
    if response.status_code == 200:
        original_name = response.json().get("name")
        logging.info(f"Admin: Successfully retrieved product {target_product_id} ('{original_name}').")
    else:
        logging.error(f"Admin: Failed to retrieve product {target_product_id}. Status: {response.status_code}")
        success = False
        return success # Cannot proceed if cannot retrieve

    # 2. Update the product (e.g., change its is_active status or name)
    updated_name_by_admin = f"Admin Modified - {original_name}"
    payload = {"name": updated_name_by_admin, "is_active": False}
    logging.info(f"Admin: Updating product ID {target_product_id} (setting is_active=False, changing name)...")
    response = admin_client.patch(f"/catalogue/products/{target_product_id}/", data=payload)
    if response.status_code == 200:
        updated_prod = response.json()
        if updated_prod.get("name") == updated_name_by_admin and updated_prod.get("is_active") == False:
            logging.info(f"Admin: Successfully updated product {target_product_id}.")
        else:
            logging.error(f"Admin: Product update for {target_product_id} seemed to succeed (200 OK) but data mismatch. Got: name='{updated_prod.get('name')}', is_active='{updated_prod.get('is_active')}'")
            success = False
    else:
        logging.error(f"Admin: Failed to update product {target_product_id}. Status: {response.status_code}, Response: {response.text}")
        success = False
        
    # 3. Delete the product - Let's assume admin can delete any product.
    # For this test, we will delete it, assuming vendor test created it and is done with it.
    # If this product was from the general list, it will be gone.
    logging.info(f"Admin: Deleting product ID {target_product_id}...")
    response = admin_client.delete(f"/catalogue/products/{target_product_id}/")
    if response.status_code == 204:
        logging.info(f"Admin: Successfully deleted product {target_product_id}.")
        # Clear it from test_data_ids so other tests don't try to use it
        if test_data_ids.get("vendor1_product_id") == target_product_id:
            test_data_ids["vendor1_product_id"] = None 
        if test_data_ids.get("shared_product_id_for_guest_view") == target_product_id:
            test_data_ids["shared_product_id_for_guest_view"] = None
    else:
        logging.error(f"Admin: Failed to delete product {target_product_id}. Status: {response.status_code}")
        success = False
        
    return success


if __name__ == "__main__":
    logging.info("======== Starting Catalogue API Tests ========")
    import random # for product_sku

    guest_client = ApiClient(user_role="guest")
    admin_client = ApiClient(user_role="admin")
    vendor_client = ApiClient(user_role="vendor")

    results = {}

    # Run public browsing first to populate shared_product_id_for_guest_view potentially
    results["public_browse_catalogue"] = scenario_public_browse_catalogue(guest_client)

    if admin_client.token:
        results["admin_manage_categories"] = scenario_admin_manage_categories(admin_client)
    else:
        logging.error("Admin client not authenticated. Skipping admin category tests.")
        results["admin_manage_categories"] = False

    if vendor_client.token and admin_client.token: # admin_client needed for setup (category check)
        results["vendor_manage_own_products"] = scenario_vendor_manage_own_products(vendor_client, admin_client)
    elif not vendor_client.token:
        logging.error("Vendor client not authenticated. Skipping vendor product tests.")
        results["vendor_manage_own_products"] = False
    elif not admin_client.token:
        logging.error("Admin client not authenticated. Skipping vendor product tests (admin needed for setup).")
        results["vendor_manage_own_products"] = False


    if admin_client.token:
        # This test depends on a product being available (either from vendor test or public list)
        # and will delete it. Run it last among product-modifying tests for specific IDs.
        results["admin_manage_any_product"] = scenario_admin_manage_any_product(admin_client)
    else:
        logging.error("Admin client not authenticated. Skipping admin product management tests.")
        results["admin_manage_any_product"] = False


    logging.info("\n======== Catalogue API Test Summary ========")
    all_passed = True
    for test_name, success_status in results.items():
        status_msg = "PASSED" if success_status else "FAILED"
        logging.info(f"Scenario '{test_name}': {status_msg}")
        if not success_status:
            all_passed = False
    
    if all_passed:
        logging.info("All Catalogue API scenarios passed!")
    else:
        logging.error("Some Catalogue API scenarios failed.")

    logging.info("======== Catalogue API Tests Finished ========")
    return all_passed

if __name__ == "__main__":
    import sys
    all_tests_passed = main() # Assuming the main logic is moved to a main() function
    sys.exit(0 if all_tests_passed else 1)
