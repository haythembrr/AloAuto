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
        logging.info(f"Fetching self ({username}) user ID using /accounts/users/ endpoint.")
        response = client.get("/accounts/users/") # Changed from /me/
        if response.status_code == 200:
            users_list = response.json().get("results", [])
            if not users_list:
                logging.error(f"No users found in response for {username} when fetching self via /accounts/users/.")
                return None

            # For non-admins, UserViewSet filters to only show current user.
            # For admins, it lists all users. We need to find the correct one.
            if client.user_role != "admin":
                if users_list[0].get("username") == username: # Should be the only one
                    logging.info(f"Successfully fetched self ID for non-admin {username}.")
                    return users_list[0].get("id")
                else:
                    logging.error(f"Non-admin {username} fetched a user, but username does not match: {users_list[0].get('username')}")
                    return None
            else: # Admin fetching self
                for user_obj in users_list:
                    if user_obj.get("username") == username:
                        logging.info(f"Successfully fetched self ID for admin {username} from user list.")
                        return user_obj.get("id")
                logging.error(f"Admin {username} could not find self in the list from /accounts/users/.")
                return None
        else:
            logging.error(f"Could not fetch users list for ({username}) ID via /accounts/users/ endpoint. Status: {response.status_code}")
            return None
    else: # Admin fetching another user
        if client.user_role == "admin":
            logging.info(f"Admin fetching other user '{username}' ID.")
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
            user_data = response.json()
            logging.info(f"Admin: Successfully retrieved user {user_id}: {user_data.get('username')}")
            # Task 2: Assertions for new fields and absence of password
            assert 'is_active' in user_data, "is_active field missing"
            assert 'created_at' in user_data, "created_at field missing"
            assert 'updated_at' in user_data, "updated_at field missing"
            assert 'password' not in user_data, "password field should not be present"
            logging.info("Admin: Verified presence of is_active, created_at, updated_at and absence of password in user details.")
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

    # 1. Retrieve own user details (using /users/{id}/)
    logging.info("Buyer: Retrieving own user details...")
    response = buyer_client.get(f"/accounts/users/{buyer_user_id}/") # Changed from /me/
    if response.status_code == 200 and response.json().get("id") == buyer_user_id:
        user_data = response.json()
        logging.info("Buyer: Successfully retrieved own user details.")
        # Task 2: Assertions for new fields and absence of password
        assert 'is_active' in user_data, "is_active field missing"
        assert 'created_at' in user_data, "created_at field missing"
        assert 'updated_at' in user_data, "updated_at field missing"
        assert 'password' not in user_data, "password field should not be present"
        logging.info("Buyer: Verified presence of is_active, created_at, updated_at and absence of password in own user details.")
    else:
        logging.error(f"Buyer: Failed to retrieve own user details. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 2. Update own user details
    updated_last_name = "UpdatedLastNameByBuyer"
    payload = {"last_name": updated_last_name}
    logging.info("Buyer: Updating own last name using /accounts/users/{buyer_user_id}/...")
    # Buyers should be able to update their own details via PATCH to /api/accounts/users/{user_id}/
    response = buyer_client.patch(f"/accounts/users/{buyer_user_id}/", data=payload)

    if response.status_code == 200 and response.json().get("last_name") == updated_last_name:
        logging.info("Buyer: Successfully updated own last name.")
    else:
        logging.error(f"Buyer: Failed to update own user details using /accounts/users/{buyer_user_id}/. Status: {response.status_code}, Text: {response.text}")
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
        # "user": test_data_ids["buyer_user_id"], # User is inferred from token
        "street": "123 Test St", # Task 1: Corrected street_address to street
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
    # "user" field is not needed as it's inferred, and usually not updatable.
    update_payload = {"city": updated_city}
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


# --- New Test Scenario: User Password Management (Task 3) ---
def scenario_user_password_change(admin_client, base_url):
    logging.info("--- Scenario: User Password Management ---")
    success = True
    test_user_username = "pw_change_user"
    initial_password = "initialPassword123"
    new_password_by_user = "newPasswordByUser456"
    new_password_by_admin = "newPasswordByAdmin789"
    user_id = None

    # 1. Admin creates a new user
    user_payload = {
        "username": test_user_username,
        "email": f"{test_user_username}@example.com",
        "password": initial_password,
        "role": "buyer", # Or any role that can log in
        "first_name": "PWTest",
        "last_name": "User"
    }
    logging.info(f"Admin: Creating user '{test_user_username}' for password change tests...")
    response_create = admin_client.post("/accounts/users/", data=user_payload)
    if response_create.status_code == 201:
        user_id = response_create.json().get("id")
        logging.info(f"Admin: Successfully created user '{test_user_username}' with ID {user_id}.")
    else:
        logging.error(f"Admin: Failed to create user for password tests. Status: {response_create.status_code}, Response: {response_create.text}")
        # Attempt to find user if already exists (e.g. from previous failed run)
        user_id = get_user_id_by_username(admin_client, test_user_username)
        if user_id:
            logging.warning(f"Admin: User '{test_user_username}' already existed. Proceeding with ID {user_id}.")
            # As admin, set their password to the known initial_password
            admin_client.patch(f"/accounts/users/{user_id}/", data={"password": initial_password})
        else:
            return False # Cannot proceed

    # 2. Verify user can log in with initial password
    logging.info(f"User '{test_user_username}': Attempting login with initial password...")
    user_client = ApiClient(user_role=None,username=test_user_username, password=initial_password, base_url=base_url)
    if user_client.token:
        logging.info(f"User '{test_user_username}': Successfully logged in with initial password.")
    else:
        logging.error(f"User '{test_user_username}': Failed to log in with initial password.")
        success = False
        # No cleanup here, admin might need to delete user if created.

    # 3. User updates their own password (via /me/ or /users/{id}/)
    if user_client.token: # Only if logged in
        logging.info(f"User '{test_user_username}': Updating own password to '{new_password_by_user}'...")
        # API might require current password for self-update, but this is not standard for DRF ModelViewSet
        # User updates own password directly using /users/{id}/ endpoint
        update_payload = {"password": new_password_by_user}
        logging.info(f"User '{test_user_username}': Attempting password update via /accounts/users/{user_id}/.")
        response_self_update = user_client.patch(f"/accounts/users/{user_id}/", data=update_payload)

        if response_self_update.status_code == 200:
            logging.info(f"User '{test_user_username}': Successfully updated own password via /users/{user_id}/.")
        else:
            logging.error(f"User '{test_user_username}': Failed to update own password via /users/{user_id}/. Status: {response_self_update.status_code}, Response: {response_self_update.text}")
            success = False
    else:
        logging.warning(f"User '{test_user_username}': Skipping self password update as not logged in.")


    # 4. Verify user can log in with new password (set by user)
    if success: # Only if previous steps including self-update were okay
        logging.info(f"User '{test_user_username}': Attempting login with new password (set by user)...")
        user_client_new_pw = ApiClient(user_role=None, username=test_user_username, password=new_password_by_user, base_url=base_url)
        if user_client_new_pw.token:
            logging.info(f"User '{test_user_username}': Successfully logged in with new password (set by user).")
        else:
            logging.error(f"User '{test_user_username}': Failed to log in with new password (set by user).")
            success = False

    # 5. Verify user can NO LONGER log in with old (initial) password
    if success: # Only if previous steps were okay
        logging.info(f"User '{test_user_username}': Attempting login with OLD (initial) password (should fail)...")
        user_client_old_pw = ApiClient(user_role=None, username=test_user_username, password=initial_password, base_url=base_url)
        if not user_client_old_pw.token:
            logging.info(f"User '{test_user_username}': Correctly FAILED to log in with old (initial) password.")
        else:
            logging.error(f"User '{test_user_username}': INCORRECTLY logged in with old (initial) password.")
            success = False
            user_client_old_pw.logout() # Logout if accidentally logged in

    # 6. (Optional) Admin changes user's password
    logging.info(f"Admin: Changing password for user '{test_user_username}' to '{new_password_by_admin}'...")
    response_admin_update = admin_client.patch(f"/accounts/users/{user_id}/", data={"password": new_password_by_admin})
    if response_admin_update.status_code == 200:
        logging.info(f"Admin: Successfully changed password for user '{test_user_username}'.")
    else:
        logging.error(f"Admin: Failed to change password for user '{test_user_username}'. Status: {response_admin_update.status_code}, Response: {response_admin_update.text}")
        success = False

    # 7. Verify user can log in with admin-set password
    if success: # Only if admin update was okay
        logging.info(f"User '{test_user_username}': Attempting login with admin-set password...")
        user_client_admin_pw = ApiClient(user_role=None,username=test_user_username, password=new_password_by_admin, base_url=base_url)
        if user_client_admin_pw.token:
            logging.info(f"User '{test_user_username}': Successfully logged in with admin-set password.")
        else:
            logging.error(f"User '{test_user_username}': Failed to log in with admin-set password.")
            success = False

    # Cleanup: Admin deletes the test user
    if user_id:
        logging.info(f"Admin: Deleting user '{test_user_username}' (ID: {user_id})...")
        response_delete = admin_client.delete(f"/accounts/users/{user_id}/")
        if response_delete.status_code == 204:
            logging.info(f"Admin: Successfully deleted user '{test_user_username}'.")
        else:
            logging.error(f"Admin: Failed to delete user '{test_user_username}'. Status: {response_delete.status_code}, Response: {response_delete.text}")
            # success = False # Don't fail the whole scenario for cleanup failure, but log it.
    return success

# --- New Test Scenario: Unique Default Addresses (Task 4) ---
def scenario_buyer_unique_default_addresses(buyer_client):
    logging.info("--- Scenario: Buyer Manages Unique Default Addresses ---")
    success = True
    user_id = test_data_ids.get("buyer_user_id")
    if not user_id:
        logging.error("Buyer: User ID not found, cannot test unique default addresses.")
        # Try to get it if not set by previous scenarios
        user_id = get_user_id_by_username(buyer_client, CREDENTIALS["buyer"]["username"])
        if not user_id: return False
        test_data_ids["buyer_user_id"] = user_id


    address_ids_cleanup = []

    def create_address(payload_override):
        base_payload = {
            "street": "Default St", "city": "DefaultVille", "state": "DS",
            "postal_code": "00000", "country": "DefaultLand",
            "is_default_shipping": False, "is_default_billing": False
        }
        payload = {**base_payload, **payload_override}
        # user field might be inferred by API from token, or might be required.
        # Current AddressViewSet.perform_create sets user=self.request.user
        # So, user field is not needed in payload.
        # payload["user"] = user_id

        response = buyer_client.post("/accounts/addresses/", data=payload)
        if response.status_code == 201:
            addr_id = response.json().get("id")
            address_ids_cleanup.append(addr_id)
            logging.info(f"Created address {addr_id} with shipping={payload['is_default_shipping']}, billing={payload['is_default_billing']}.")
            return addr_id
        else:
            logging.error(f"Failed to create address. Payload: {payload}, Status: {response.status_code}, Response: {response.text}")
            return None

    def get_address_details(addr_id):
        response = buyer_client.get(f"/accounts/addresses/{addr_id}/")
        if response.status_code == 200:
            return response.json()
        logging.error(f"Failed to get address {addr_id} details. Status: {response.status_code}")
        return None

    def update_address(addr_id, payload_override):
        response = buyer_client.patch(f"/accounts/addresses/{addr_id}/", data=payload_override)
        if response.status_code == 200:
            logging.info(f"Updated address {addr_id} with {payload_override}.")
            return response.json()
        else:
            logging.error(f"Failed to update address {addr_id}. Status: {response.status_code}, Response: {response.text}")
            return None

    # --- Test is_default_shipping ---
    logging.info("Testing unique default shipping address...")
    # A. Create Address 1, mark is_default_shipping=True
    addr1_id = create_address({"street": "1 Ship St", "is_default_shipping": True})
    if not addr1_id: success = False; return success # Early exit if creation fails

    addr1_details = get_address_details(addr1_id)
    if not (addr1_details and addr1_details.get("is_default_shipping") == True):
        logging.error("Address 1 was not set as default shipping upon creation.")
        success = False

    # B. Create Address 2, mark is_default_shipping=True
    if success:
        addr2_id = create_address({"street": "2 Ship St", "is_default_shipping": True})
        if not addr2_id: success = False; return success

        addr1_details = get_address_details(addr1_id) # Re-fetch addr1
        addr2_details = get_address_details(addr2_id)

        if not (addr2_details and addr2_details.get("is_default_shipping") == True):
            logging.error("Address 2 was not set as default shipping.")
            success = False
        if not (addr1_details and addr1_details.get("is_default_shipping") == False):
            logging.error("Address 1 did not become non-default shipping after Address 2 was made default.")
            success = False

    # C. Update Address 1, set is_default_shipping=True
    if success:
        update_response = update_address(addr1_id, {"is_default_shipping": True})
        if not update_response: success = False; return success

        addr1_details = get_address_details(addr1_id)
        addr2_details = get_address_details(addr2_id) # Re-fetch addr2

        if not (addr1_details and addr1_details.get("is_default_shipping") == True):
            logging.error("Address 1 was not set as default shipping upon update.")
            success = False
        if not (addr2_details and addr2_details.get("is_default_shipping") == False):
            logging.error("Address 2 did not become non-default shipping after Address 1 was updated to default.")
            success = False

    # --- Test is_default_billing ---
    # Reset: ensure all existing test addresses for this scenario are not default billing
    for addr_id_clean in address_ids_cleanup:
        update_address(addr_id_clean, {"is_default_billing": False})

    logging.info("Testing unique default billing address...")
    # A. Create Address 3 (use addr1_id for simplicity if available, or create new), mark is_default_billing=True
    # Let's use existing ones to reduce creations, then clean them up.
    # First, ensure addr1 and addr2 are not default billing from previous tests.
    if addr1_id: update_address(addr1_id, {"is_default_billing": False, "street": "1 Bill St"})
    if 'addr2_id' in locals() and addr2_id: update_address(addr2_id, {"is_default_billing": False, "street": "2 Bill St"})

    addr3_id = create_address({"street": "3 Bill St", "is_default_billing": True})
    if not addr3_id: success = False; return success

    addr3_details = get_address_details(addr3_id)
    if not (addr3_details and addr3_details.get("is_default_billing") == True):
        logging.error("Address 3 was not set as default billing upon creation.")
        success = False

    # B. Create Address 4, mark is_default_billing=True
    if success:
        addr4_id = create_address({"street": "4 Bill St", "is_default_billing": True})
        if not addr4_id: success = False; return success

        addr3_details = get_address_details(addr3_id) # Re-fetch addr3
        addr4_details = get_address_details(addr4_id)

        if not (addr4_details and addr4_details.get("is_default_billing") == True):
            logging.error("Address 4 was not set as default billing.")
            success = False
        if not (addr3_details and addr3_details.get("is_default_billing") == False):
            logging.error("Address 3 did not become non-default billing after Address 4 was made default.")
            success = False

    # C. Update Address 3, set is_default_billing=True
    if success:
        update_response = update_address(addr3_id, {"is_default_billing": True})
        if not update_response: success = False; return success

        addr3_details = get_address_details(addr3_id)
        addr4_details = get_address_details(addr4_id) # Re-fetch addr4

        if not (addr3_details and addr3_details.get("is_default_billing") == True):
            logging.error("Address 3 was not set as default billing upon update.")
            success = False
        if not (addr4_details and addr4_details.get("is_default_billing") == False):
            logging.error("Address 4 did not become non-default billing after Address 3 was updated to default.")
            success = False

    # E. Clean up created addresses
    logging.info(f"Cleaning up {len(address_ids_cleanup)} addresses created for unique default test...")
    for addr_id in address_ids_cleanup:
        del_response = buyer_client.delete(f"/accounts/addresses/{addr_id}/")
        if del_response.status_code == 204:
            logging.info(f"Successfully deleted address {addr_id}.")
        else:
            logging.warning(f"Failed to delete address {addr_id}. Status: {del_response.status_code}")
            # Not failing the test for cleanup failure, but it's good to note.

    return success


def main(): # Renamed from if __name__ == "__main__": block to be callable
    logging.info("======== Starting Accounts API Tests ========")

    # Initialize clients
    admin_client = ApiClient(user_role="admin") # Assuming base_url is set in ApiClient's constructor or globally
    buyer_client = ApiClient(user_role="buyer")
    base_url = admin_client.base_url # Get base_url from an initialized client

    results = {}

    if not admin_client.token:
        logging.error("Admin client failed to authenticate. Skipping admin tests.")
    else:
        results["admin_manage_users"] = scenario_admin_manage_users(admin_client)
        # User password change scenario needs admin client and base_url for new client instantiation
        results["user_password_change"] = scenario_user_password_change(admin_client, base_url)


    if not buyer_client.token:
        logging.error("Buyer client failed to authenticate. Skipping buyer tests.")
    else:
        results["buyer_manage_own_account"] = scenario_buyer_manage_own_account(buyer_client)
        results["buyer_manage_addresses"] = scenario_buyer_manage_addresses(buyer_client)
        results["buyer_unique_default_addresses"] = scenario_buyer_unique_default_addresses(buyer_client)


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
