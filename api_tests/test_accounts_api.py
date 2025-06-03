import logging
from api_client import ApiClient, CREDENTIALS # Assuming CREDENTIALS provides usernames for fetching IDs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

# Store IDs fetched during tests to use in subsequent tests (e.g., created address ID)
test_data_ids = {
    "buyer_user_id": None,
    "buyer_address_id": None,
    "admin_managed_user_id": None, # For admin to manage another user
}

def get_user_id_by_username(client, username):
    """Helper to get user ID by username. Assumes an admin client and an endpoint that allows this."""
    if client.user_role != "admin":
        logging.warning("Attempting to get user ID by username without admin privileges. This might fail.")

    # This endpoint might not exist or might have different filtering.
    # Common DRF practice is /api/accounts/users/ or similar.
    # We assume it supports ?username=... query param or similar.
    # If not, this helper needs adjustment or we rely on IDs known from population.
    # For now, let's assume the user data from CREDENTIALS is what we need for self-tests.

    # Fallback: For testing, we often need the ID of the *current* user.
    # The "me" endpoint or profile endpoint is common for this.
    # Let's assume /api/accounts/users/me/ exists for authenticated users.
    if username == CREDENTIALS[client.user_role]["username"]: # If fetching self
        response = client.get("/accounts/users/me/")
        if response.status_code == 200:
            return response.json().get("id")
        else:
            logging.error(f"Could not fetch current user's ({username}) ID via /me/ endpoint. Status: {response.status_code}")
            # Try to list all users and find by username if admin
            if client.user_role == "admin":
                response_users = client.get("/accounts/users/")
                if response_users.status_code == 200:
                    for user in response_users.json().get("results", []): # Assuming pagination
                        if user.get("username") == username:
                            return user.get("id")
                logging.error(f"Could not find user {username} by listing users as admin.")
            return None
    else: # Admin fetching another user
        if client.user_role == "admin":
            response_users = client.get(f"/accounts/users/?username={username}") # Assumes username filter works
            users_list = response_users.json().get("results", [])
            if response_users.status_code == 200 and users_list:
                return users_list[0].get("id")
            # If no direct username filter, try listing all and finding
            response_all_users = client.get("/accounts/users/")
            if response_all_users.status_code == 200:
                for user_obj in response_all_users.json().get("results", []):
                    if user_obj.get("username") == username:
                        return user_obj.get("id")
            logging.error(f"Admin could not find user {username} by username filter or list.")
            return None
    return None


# --- Test Scenarios ---

def scenario_admin_manage_users(admin_client):
    logging.info("--- Scenario: Admin Manages Users ---")
    success = True

    # 1. List Users
    logging.info("Admin: Listing users...")
    response = admin_client.get("/accounts/users/")
    if response.status_code == 200:
        users_list = response.json().get("results", []) # Assuming paginated response
        logging.info(f"Admin: Successfully listed {len(users_list)} users (first page).")
        # Find a non-admin user to manage, if possible (e.g., our buyer_test_api_user)
        buyer_username = CREDENTIALS["buyer"]["username"]
        for user_details in users_list:
            if user_details.get("username") == buyer_username:
                test_data_ids["admin_managed_user_id"] = user_details.get("id")
                logging.info(f"Admin: Found buyer user '{buyer_username}' with ID {test_data_ids['admin_managed_user_id']} to manage.")
                break
        if not test_data_ids["admin_managed_user_id"]:
             # if not found on first page, try direct fetch by username (if supported by API)
            test_data_ids["admin_managed_user_id"] = get_user_id_by_username(admin_client, buyer_username)

    else:
        logging.error(f"Admin: Failed to list users. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 2. Retrieve a specific user (if ID was found)
    if test_data_ids["admin_managed_user_id"]:
        user_id = test_data_ids["admin_managed_user_id"]
        logging.info(f"Admin: Retrieving user ID {user_id}...")
        response = admin_client.get(f"/accounts/users/{user_id}/")
        if response.status_code == 200:
            logging.info(f"Admin: Successfully retrieved user {user_id}: {response.json().get('username')}")
        else:
            logging.error(f"Admin: Failed to retrieve user {user_id}. Status: {response.status_code}")
            success = False
    else:
        logging.warning("Admin: Skipping retrieve/update user tests as no non-admin user ID was found/set.")
        # success = False # Or just skip these tests without failing the scenario

    # 3. Update a user (e.g., change their first name)
    if test_data_ids["admin_managed_user_id"]:
        user_id = test_data_ids["admin_managed_user_id"]
        updated_first_name = "UpdatedFirstNameByAdmin"
        payload = {"first_name": updated_first_name}
        logging.info(f"Admin: Updating first name for user ID {user_id}...")
        response = admin_client.patch(f"/accounts/users/{user_id}/", data=payload)
        if response.status_code == 200 and response.json().get("first_name") == updated_first_name:
            logging.info(f"Admin: Successfully updated user {user_id}'s first name.")
        else:
            logging.error(f"Admin: Failed to update user {user_id}. Status: {response.status_code}, Response: {response.text}")
            success = False

    # 4. Delete a user - SKIPPING for now to keep test users, unless we create a disposable one.
    # logging.info("Admin: Deleting a user (skipped for now)...")

    return success

def scenario_buyer_manage_own_account(buyer_client):
    logging.info("--- Scenario: Buyer Manages Own Account ---")
    success = True

    # 0. Get own user ID
    buyer_user_id = get_user_id_by_username(buyer_client, CREDENTIALS["buyer"]["username"])
    if not buyer_user_id:
        logging.error("Buyer: Could not retrieve own user ID. Cannot proceed with account management tests.")
        return False
    test_data_ids["buyer_user_id"] = buyer_user_id
    logging.info(f"Buyer: Own user ID is {buyer_user_id}.")

    # 1. Retrieve own user details (using /me/ or /users/{id}/)
    logging.info("Buyer: Retrieving own user details...")
    response = buyer_client.get("/accounts/users/me/") # Or f"/accounts/users/{buyer_user_id}/"
    if response.status_code == 200 and response.json().get("id") == buyer_user_id:
        logging.info("Buyer: Successfully retrieved own user details.")
    else:
        logging.error(f"Buyer: Failed to retrieve own user details. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 2. Update own user details
    updated_last_name = "UpdatedLastNameByBuyer"
    payload = {"last_name": updated_last_name}
    logging.info("Buyer: Updating own last name...")
    # Buyers might only be able to update their own details via /me/ or /profile/ endpoint, not /users/{id}/
    response = buyer_client.patch("/accounts/users/me/update/", data=payload) # Assuming an endpoint like this, or /users/me/
    # If the API uses PUT on /users/me/ and requires all fields, this test would need adjustment.
    # A common pattern is PATCH to /users/me/ or a dedicated profile endpoint.
    # Let's assume PATCH to /api/accounts/users/{user_id}/ is allowed for self
    # response_update_self = buyer_client.patch(f"/accounts/users/{buyer_user_id}/", data=payload)


    if response.status_code == 200 and response.json().get("last_name") == updated_last_name:
        logging.info("Buyer: Successfully updated own last name.")
    else:
        # Fallback: try updating via /users/{id}/ if /me/update didn't work or doesn't exist
        logging.warning(f"Buyer: Update via /accounts/users/me/update/ failed (Status: {response.status_code}). Trying /accounts/users/{buyer_user_id}/")
        response_alt = buyer_client.patch(f"/accounts/users/{buyer_user_id}/", data=payload)
        if response_alt.status_code == 200 and response_alt.json().get("last_name") == updated_last_name:
            logging.info("Buyer: Successfully updated own last name via /users/{id}/.")
        else:
            logging.error(f"Buyer: Failed to update own user details. Main attempt Status: {response.status_code}, Text: {response.text}. Alt attempt Status: {response_alt.status_code}, Text: {response_alt.text}")
            success = False


    # 3. Attempt to list users (should be denied)
    logging.info("Buyer: Attempting to list all users (should be denied)...")
    response = buyer_client.get("/accounts/users/")
    if response.status_code == 403: # Forbidden
        logging.info("Buyer: Correctly denied access to list all users (403 Forbidden).")
    else:
        logging.error(f"Buyer: Incorrectly allowed/failed to list users. Status: {response.status_code}")
        success = False

    return success

def scenario_buyer_manage_addresses(buyer_client):
    logging.info("--- Scenario: Buyer Manages Addresses ---")
    success = True
    if not test_data_ids.get("buyer_user_id"):
        logging.error("Buyer: User ID not found, cannot manage addresses.")
        # Attempt to get it now
        buyer_user_id = get_user_id_by_username(buyer_client, CREDENTIALS["buyer"]["username"])
        if not buyer_user_id: return False
        test_data_ids["buyer_user_id"] = buyer_user_id


    # 1. Create an address
    address_payload = {
        "user": test_data_ids["buyer_user_id"], # Some APIs might infer user from token
        "street_address": "123 Test St",
        "city": "Testville",
        "state": "TS",
        "postal_code": "12345",
        "country": "Testland",
        "is_default_shipping": True,
        "is_default_billing": True
    }
    logging.info("Buyer: Creating an address...")
    response = buyer_client.post("/accounts/addresses/", data=address_payload)
    if response.status_code == 201: # Created
        created_address = response.json()
        test_data_ids["buyer_address_id"] = created_address.get("id")
        logging.info(f"Buyer: Successfully created address with ID {test_data_ids['buyer_address_id']}.")
    else:
        logging.error(f"Buyer: Failed to create address. Status: {response.status_code}, Response: {response.text}")
        success = False
        return success # Cannot proceed without address ID

    address_id = test_data_ids["buyer_address_id"]

    # 2. List own addresses
    logging.info("Buyer: Listing own addresses...")
    response = buyer_client.get("/accounts/addresses/") # Assumes it's filtered by user
    if response.status_code == 200:
        addresses = response.json().get("results", [])
        found = any(addr.get("id") == address_id for addr in addresses)
        if found:
            logging.info(f"Buyer: Successfully listed own addresses, found created address {address_id}.")
        else:
            logging.error(f"Buyer: Listed addresses, but created address ID {address_id} not found in response: {addresses}")
            success = False
    else:
        logging.error(f"Buyer: Failed to list own addresses. Status: {response.status_code}")
        success = False

    # 3. Retrieve the created address
    logging.info(f"Buyer: Retrieving address ID {address_id}...")
    response = buyer_client.get(f"/accounts/addresses/{address_id}/")
    if response.status_code == 200 and response.json().get("city") == "Testville":
        logging.info(f"Buyer: Successfully retrieved address {address_id}.")
    else:
        logging.error(f"Buyer: Failed to retrieve address {address_id}. Status: {response.status_code}")
        success = False

    # 4. Update the address
    updated_city = "NewTestCity"
    update_payload = {"city": updated_city, "user": test_data_ids["buyer_user_id"]} # some fields might be required on PUT/PATCH
    logging.info(f"Buyer: Updating address ID {address_id}...")
    response = buyer_client.patch(f"/accounts/addresses/{address_id}/", data=update_payload) # Using PATCH
    if response.status_code == 200 and response.json().get("city") == updated_city:
        logging.info(f"Buyer: Successfully updated address {address_id}.")
    else:
        logging.error(f"Buyer: Failed to update address {address_id}. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 5. Delete the address
    logging.info(f"Buyer: Deleting address ID {address_id}...")
    response = buyer_client.delete(f"/accounts/addresses/{address_id}/")
    if response.status_code == 204: # No Content
        logging.info(f"Buyer: Successfully deleted address {address_id}.")
    else:
        logging.error(f"Buyer: Failed to delete address {address_id}. Status: {response.status_code}")
        success = False

    # Verify deletion
    if success: # Only if delete was reported as success
        logging.info(f"Buyer: Verifying deletion of address ID {address_id}...")
        response = buyer_client.get(f"/accounts/addresses/{address_id}/")
        if response.status_code == 404: # Not Found
            logging.info(f"Buyer: Address {address_id} successfully verified as deleted (404 Not Found).")
        else:
            logging.error(f"Buyer: Address {address_id} still found after delete attempt. Status: {response.status_code}")
            success = False

    return success


if __name__ == "__main__":
    logging.info("======== Starting Accounts API Tests ========")

    # Initialize clients
    admin_client = ApiClient(user_role="admin")
    buyer_client = ApiClient(user_role="buyer")

    results = {}

    if not admin_client.token:
        logging.error("Admin client failed to authenticate. Skipping admin tests.")
    else:
        results["admin_manage_users"] = scenario_admin_manage_users(admin_client)

    if not buyer_client.token:
        logging.error("Buyer client failed to authenticate. Skipping buyer tests.")
    else:
        results["buyer_manage_own_account"] = scenario_buyer_manage_own_account(buyer_client)
        results["buyer_manage_addresses"] = scenario_buyer_manage_addresses(buyer_client)

    logging.info("\n======== Accounts API Test Summary ========")
    all_passed = True
    for test_name, success_status in results.items():
        status_msg = "PASSED" if success_status else "FAILED"
        logging.info(f"Scenario '{test_name}': {status_msg}")
        if not success_status:
            all_passed = False

    if all_passed:
        logging.info("All Accounts API scenarios passed!")
    else:
        logging.error("Some Accounts API scenarios failed.")

    logging.info("======== Accounts API Tests Finished ========")
    return all_passed

if __name__ == "__main__":
    import sys
    # This ensures that if this script is run directly, it behaves like a test script.
    # The run_api_tests.py script will call main() directly.
    all_tests_passed = main()
    sys.exit(0 if all_tests_passed else 1)
