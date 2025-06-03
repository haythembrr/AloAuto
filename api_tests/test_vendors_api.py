import logging
from api_client import ApiClient, CREDENTIALS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

test_data_ids = {
    "vendor1_user_id": None,
    "vendor1_profile_id": None, # This is the ID of the Vendor object in vendors.Vendor
    "vendor2_user_id": None,
    "vendor2_profile_id": None,
}

def get_user_id_and_vendor_profile_id(client, target_username):
    """
    Fetches User ID and associated Vendor Profile ID for a given username.
    Assumes client is authenticated (preferably as admin for broad access, or as self).
    """
    user_id = None
    vendor_profile_id = None

    # 1. Get User ID
    user_response = client.get(f"/accounts/users/?username={target_username}") # Assumes admin or self can query by username
    if user_response.status_code == 200:
        users = user_response.json().get("results", [])
        if users:
            user_id = users[0].get("id")
            logging.info(f"Found user ID for {target_username}: {user_id}")
        else:
            logging.warning(f"User {target_username} not found via /accounts/users/ endpoint.")
            # Fallback: try /me/ if target_username is self
            if client.user_role != "admin" and CREDENTIALS.get(client.user_role, {}).get("username") == target_username:
                me_response = client.get("/accounts/users/me/")
                if me_response.status_code == 200:
                    user_id = me_response.json().get("id")
                    logging.info(f"Found self user ID for {target_username} via /me/: {user_id}")

    if not user_id:
        logging.error(f"Could not determine user ID for {target_username}.")
        return None, None

    # 2. Get Vendor Profile ID using the User ID (assuming vendor profiles are linked via user_id)
    # The endpoint /vendors/ might list all vendors (for admin) or filter by current user (for vendor)
    # Or there might be a /vendors/?user_id={user_id} or /vendors/my-profile/

    # Try fetching vendor profile assuming the client is the vendor themselves
    if CREDENTIALS.get(client.user_role, {}).get("username") == target_username:
        logging.info(f"Attempting to fetch vendor profile for self ({target_username}) via /vendors/my-profile/ or similar...")
        # Option A: A dedicated endpoint like /vendors/my-profile/ (hypothetical)
        # response_vendor_profile = client.get("/vendors/my-profile/")
        # if response_vendor_profile.status_code == 200:
        #     vendor_profile_id = response_vendor_profile.json().get("id")

        # Option B: List /vendors/ and expect it to be filtered to the current user's vendor profile
        # This is a common pattern if a vendor user can only have one vendor profile.
        if not vendor_profile_id:
            response_vendor_list = client.get("/vendors/")
            if response_vendor_list.status_code == 200:
                vendor_profiles = response_vendor_list.json().get("results", [])
                if vendor_profiles: # Assuming it returns a list, even if just one for the current vendor
                    # We need to ensure this is the correct vendor profile if list can contain multiple for admin
                    # For a vendor user, it's usually just their own.
                    for vp in vendor_profiles:
                        if vp.get("user") == user_id or vp.get("user_details", {}).get("id") == user_id : # Check if user foreign key matches
                            vendor_profile_id = vp.get("id")
                            break
                    if vendor_profiles and not vendor_profile_id: # if list is not empty but no match (e.g. user field is just ID)
                        # this case is tricky, depends on serializer for vendor list.
                        # if user field is just an ID, we might need to iterate and check.
                        # For now, if it's a list, take the first if it's the only one.
                        if len(vendor_profiles) == 1:
                           # Check if the 'user' field of the vendor profile matches our user_id
                           # The structure of vendor profile JSON (is 'user' an ID or a nested object?) matters here
                           # Let's assume 'user' (user_id) or 'user_details.id' is present in vendor profile serializer
                           potential_vp = vendor_profiles[0]
                           if potential_vp.get("user") == user_id or (isinstance(potential_vp.get("user"), dict) and potential_vp.get("user").get("id") == user_id):
                               vendor_profile_id = potential_vp.get("id")
                           else: # Try to get the vendor_id from the user object if it's there
                                me_response = client.get("/accounts/users/me/")
                                if me_response.status_code == 200:
                                    vendor_profile_id = me_response.json().get("vendor_id") # If user serializer has vendor_id

    # If admin is fetching for another user, or the above failed:
    if not vendor_profile_id and client.user_role == "admin":
        logging.info(f"Admin client attempting to find vendor profile for user_id {user_id} by listing all vendors.")
        response_vendor_list = client.get("/vendors/") # Admin gets all
        if response_vendor_list.status_code == 200:
            all_vendors = response_vendor_list.json().get("results", [])
            for vendor in all_vendors:
                # Check based on how user is represented in vendor details:
                # 1. Direct user ID: vendor.get("user") == user_id
                # 2. Nested user object: vendor.get("user", {}).get("id") == user_id
                # 3. Username in user object: vendor.get("user", {}).get("username") == target_username
                user_info = vendor.get("user")
                user_matches = False
                if isinstance(user_info, int) and user_info == user_id: # Direct ID
                    user_matches = True
                elif isinstance(user_info, dict): # Nested object
                    if user_info.get("id") == user_id or user_info.get("username") == target_username:
                        user_matches = True

                if user_matches:
                    vendor_profile_id = vendor.get("id")
                    break

    if vendor_profile_id:
        logging.info(f"Found vendor profile ID for user {target_username} (User ID: {user_id}): {vendor_profile_id}")
    else:
        logging.warning(f"Vendor profile ID not found for user {target_username} (User ID: {user_id}).")
        # This might be normal if the user is not a vendor or has no profile yet.

    return user_id, vendor_profile_id


def scenario_vendor_manage_own_profile(vendor_client, vendor_username_key="vendor"):
    logging.info(f"--- Scenario: Vendor ({CREDENTIALS[vendor_username_key]['username']}) Manages Own Profile ---")
    success = True

    vendor_user_id, vendor_profile_id = get_user_id_and_vendor_profile_id(vendor_client, CREDENTIALS[vendor_username_key]["username"])

    if not vendor_user_id:
        logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Could not get own User ID. Aborting profile tests.")
        return False
    if not vendor_profile_id:
        # This could mean the vendor profile wasn't auto-created by a signal when user was made.
        # Or the get_user_id_and_vendor_profile_id logic needs refinement for vendor role.
        # For now, let's assume a vendor profile SHOULD exist if populate_vendors ran.
        logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Could not find own Vendor Profile ID. populate_vendors might not have run or profile not linked.")
        return False

    if vendor_username_key == "vendor":
        test_data_ids["vendor1_user_id"] = vendor_user_id
        test_data_ids["vendor1_profile_id"] = vendor_profile_id
    elif vendor_username_key == "vendor2":
        test_data_ids["vendor2_user_id"] = vendor_user_id
        test_data_ids["vendor2_profile_id"] = vendor_profile_id

    # 1. Retrieve own vendor profile
    logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Retrieving own vendor profile (ID: {vendor_profile_id})...")
    # Common REST pattern: /api/vendors/{id}/
    response = vendor_client.get(f"/vendors/{vendor_profile_id}/")
    if response.status_code == 200:
        logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Successfully retrieved own profile. Company: {response.json().get('company_name')}")
    else:
        logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Failed to retrieve own profile. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 2. Update own vendor profile
    updated_description = f"Updated description by {CREDENTIALS[vendor_username_key]['username']} at {logging.getLogger().name}" # Ensure it's unique enough for test
    payload = {"description": updated_description, "user": vendor_user_id} # 'user' might be read-only or not required in payload

    logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Updating own vendor profile (ID: {vendor_profile_id})...")
    response = vendor_client.patch(f"/vendors/{vendor_profile_id}/", data=payload)
    if response.status_code == 200:
        if response.json().get("description") == updated_description:
            logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Successfully updated own profile description.")
        else:
            logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Profile description update seemed to succeed (200 OK) but content mismatch. Expected '{updated_description}', got '{response.json().get('description')}'")
            success = False
    else:
        logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Failed to update own profile. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 3. Attempt to list ALL vendor profiles (should be denied or limited to own if not admin)
    logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Attempting to list all vendors...")
    response = vendor_client.get("/vendors/")
    if response.status_code == 200:
        # Check if only their own profile is listed (or if it's an admin-like full list)
        vendors_list = response.json().get("results", [])
        is_own_profile_only = len(vendors_list) == 1 and vendors_list[0].get("id") == vendor_profile_id
        if is_own_profile_only:
            logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Successfully listed vendors (filtered to own profile).")
        elif len(vendors_list) > 1 : # Vendor sees more than just their own - this might be an issue or by design
            logging.warning(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Listed multiple vendor profiles ({len(vendors_list)}). This might be broader access than typical for a vendor role.")
            # This is not necessarily a failure of the test, but a point of observation for API design.
        else: # Empty list or wrong item
            logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Listed vendors, but own profile not found or list incorrect. Count: {len(vendors_list)}")
            success = False

    elif response.status_code == 403: # More typical if vendors cannot list others
        logging.info(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Correctly denied from listing all vendor profiles widely (403 Forbidden).")
    else:
        logging.error(f"Vendor ({CREDENTIALS[vendor_username_key]['username']}): Error listing vendors. Status: {response.status_code}")
        success = False

    return success

def scenario_admin_manage_vendor_profiles(admin_client):
    logging.info("--- Scenario: Admin Manages Vendor Profiles ---")
    success = True

    # We need a vendor profile ID to manage. Let's use vendor1's profile if available.
    # Ensure vendor1_profile_id is fetched if not already
    if not test_data_ids.get("vendor1_profile_id"):
        _, test_data_ids["vendor1_profile_id"] = get_user_id_and_vendor_profile_id(admin_client, CREDENTIALS["vendor"]["username"])

    target_vendor_profile_id = test_data_ids.get("vendor1_profile_id")

    if not target_vendor_profile_id:
        logging.error("Admin: No vendor profile ID (vendor1) found to manage. populate_vendors or ID fetching might have issues.")
        return False

    # 1. List all vendor profiles
    logging.info("Admin: Listing all vendor profiles...")
    response = admin_client.get("/vendors/")
    if response.status_code == 200:
        vendors_count = response.json().get("count", len(response.json().get("results", []))) # Handle paginated or non-paginated
        logging.info(f"Admin: Successfully listed {vendors_count} vendor profiles.")
        # Verify our target vendor is in the list
        found_target = False
        for vendor_profile in response.json().get("results", []):
            if vendor_profile.get("id") == target_vendor_profile_id:
                found_target = True
                break
        if not found_target:
            # Check subsequent pages if paginated
            current_page = response.json()
            while current_page.get("next") and not found_target:
                logging.info(f"Admin: Checking next page for vendor ID {target_vendor_profile_id}...")
                page_response = admin_client.get(current_page["next"]) # Assumes full URL in 'next'
                if page_response.status_code == 200:
                    current_page = page_response.json()
                    for vp_data in current_page.get("results",[]):
                        if vp_data.get("id") == target_vendor_profile_id:
                            found_target = True
                            break
                else:
                    logging.error(f"Admin: Failed to fetch next page {current_page.get('next')}. Status: {page_response.status_code}")
                    break # Stop paginating on error
            if not found_target:
                 logging.warning(f"Admin: Listed vendors, but target vendor profile ID {target_vendor_profile_id} not found in the list.")
                 # success = False # This could be a strict failure or just a warning
    else:
        logging.error(f"Admin: Failed to list vendor profiles. Status: {response.status_code}")
        success = False

    # 2. Retrieve a specific vendor profile
    logging.info(f"Admin: Retrieving vendor profile ID {target_vendor_profile_id}...")
    response = admin_client.get(f"/vendors/{target_vendor_profile_id}/")
    if response.status_code == 200:
        logging.info(f"Admin: Successfully retrieved vendor profile {target_vendor_profile_id}. Company: {response.json().get('company_name')}")
    else:
        logging.error(f"Admin: Failed to retrieve vendor profile {target_vendor_profile_id}. Status: {response.status_code}")
        success = False

    # 3. Update a vendor profile (e.g., change status - 'approve' or 'suspend')
    # Assuming 'status' is a valid field. From populate_vendors, statuses include 'pending', 'approved', 'rejected', 'suspended'.
    new_status = "approved" # Or "suspended" if already approved
    # Check current status to toggle
    current_status = response.json().get("status")
    if current_status == "approved":
        new_status = "suspended"

    payload = {"status": new_status}
    logging.info(f"Admin: Updating vendor profile ID {target_vendor_profile_id} status to '{new_status}'...")
    response = admin_client.patch(f"/vendors/{target_vendor_profile_id}/", data=payload)
    if response.status_code == 200 and response.json().get("status") == new_status:
        logging.info(f"Admin: Successfully updated vendor profile {target_vendor_profile_id} status to '{new_status}'.")
    else:
        logging.error(f"Admin: Failed to update vendor profile {target_vendor_profile_id} status. Status: {response.status_code}, Response: {response.text}")
        success = False

    # 4. Delete a vendor profile - SKIPPING for now to keep test vendor profiles
    # logging.info("Admin: Deleting a vendor profile (skipped)...")

    return success

def scenario_public_view_vendors(guest_client):
    logging.info("--- Scenario: Public User Views Vendor Information ---")
    success = True

    # 1. List vendor profiles (publicly accessible list, maybe limited fields)
    logging.info("Public: Attempting to list vendor profiles...")
    response = guest_client.get("/vendors/") # No auth
    if response.status_code == 200:
        vendors_count = response.json().get("count", len(response.json().get("results", [])))
        logging.info(f"Public: Successfully listed {vendors_count} vendor profiles.")
        # Check if sensitive data is exposed - this is more of a manual check or deeper inspection.
        # For now, just checking accessibility.
    elif response.status_code == 401 or response.status_code == 403: # Unauthorized or Forbidden
        logging.info("Public: Listing vendor profiles is not allowed for unauthenticated users (as expected for some designs).")
        # This is not a failure, but depends on product requirements. Let's assume for now it's okay if it's restricted.
    else:
        logging.error(f"Public: Error listing vendor profiles. Status: {response.status_code}, Response: {response.text}")
        success = False # Failure if it's an unexpected error

    # 2. Retrieve a specific vendor profile (if IDs are known or guessable, and if public detail view exists)
    # This usually requires an ID. If listing is not public, getting an ID is hard.
    # Let's assume if listing is public, we can try to get the first one.
    if response.status_code == 200 and response.json().get("results"):
        first_vendor_id = response.json()["results"][0].get("id")
        if first_vendor_id:
            logging.info(f"Public: Attempting to retrieve vendor profile ID {first_vendor_id}...")
            response_detail = guest_client.get(f"/vendors/{first_vendor_id}/")
            if response_detail.status_code == 200:
                logging.info(f"Public: Successfully retrieved vendor profile {first_vendor_id}.")
            elif response_detail.status_code == 401 or response_detail.status_code == 403:
                 logging.info(f"Public: Detail view for vendor profile {first_vendor_id} is not allowed for unauthenticated users.")
            else:
                logging.error(f"Public: Error retrieving vendor profile {first_vendor_id}. Status: {response_detail.status_code}")
                success = False
    elif response.status_code == 200 : # list was successful but empty
        logging.info("Public: Vendor list is empty, skipping public detail view test.")
    else: # Listing was not successful (e.g. 401/403)
        logging.info("Public: Skipping detail view test as vendor listing was not accessible/successful.")

    return success


if __name__ == "__main__":
    logging.info("======== Starting Vendor API Tests ========")

    admin_client = ApiClient(user_role="admin")
    vendor_client = ApiClient(user_role="vendor") # vendor_test_api_user
    # vendor2_client = ApiClient(user_role="vendor2") # vendor2_test_api_user - if needed for specific tests
    guest_client = ApiClient(user_role="guest") # Unauthenticated

    results = {}

    # Pre-fetch IDs for vendor1 using admin client for broader permissions during ID fetch
    # This helps ensure IDs are available before vendor-specific tests run.
    if admin_client.token:
        test_data_ids["vendor1_user_id"], test_data_ids["vendor1_profile_id"] = \
            get_user_id_and_vendor_profile_id(admin_client, CREDENTIALS["vendor"]["username"])
    else:
        logging.error("Admin client failed to auth. Vendor ID pre-fetch might fail or be incomplete.")
        # Fallback: vendor client tries to fetch its own IDs if admin can't.

    if vendor_client.token:
        results["vendor_manage_own_profile"] = scenario_vendor_manage_own_profile(vendor_client, "vendor")
    else:
        logging.error(f"Vendor ({CREDENTIALS['vendor']['username']}) client failed to authenticate. Skipping its tests.")
        results["vendor_manage_own_profile"] = False

    if admin_client.token:
        results["admin_manage_vendor_profiles"] = scenario_admin_manage_vendor_profiles(admin_client)
    else:
        logging.error("Admin client failed to authenticate. Skipping admin-vendor tests.")
        results["admin_manage_vendor_profiles"] = False

    results["public_view_vendors"] = scenario_public_view_vendors(guest_client)

    logging.info("\n======== Vendor API Test Summary ========")
    all_passed = True
    for test_name, success_status in results.items():
        status_msg = "PASSED" if success_status else "FAILED"
        logging.info(f"Scenario '{test_name}': {status_msg}")
        if not success_status:
            all_passed = False

    if all_passed:
        logging.info("All Vendor API scenarios passed (or were appropriately restricted)!")
    else:
        logging.error("Some Vendor API scenarios failed.")

    logging.info("======== Vendor API Tests Finished ========")
    return all_passed

if __name__ == "__main__":
    import sys
    all_tests_passed = main()
    sys.exit(0 if all_tests_passed else 1)
