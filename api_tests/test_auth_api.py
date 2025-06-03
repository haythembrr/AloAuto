import logging
from api_client import ApiClient, CREDENTIALS, STANDARD_PASSWORD, BASE_URL, USER_TOKENS
import requests # For specific exception handling if needed

# Configure logging for test script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(module)s] - %(message)s')

def test_successful_login(user_role):
    logging.info(f"--- Test: Successful Login for {user_role.upper()} ---")
    try:
        # Clear existing token for this role to force a new login
        if user_role in USER_TOKENS:
            del USER_TOKENS[user_role]

        client = ApiClient(user_role=user_role)
        assert client.token is not None, f"Token should not be None for {user_role}"
        assert client.user_role == user_role, f"Client user_role should be {user_role}"
        logging.info(f"SUCCESS: {user_role.upper()} login successful. Token received and client configured.")
        return True
    except Exception as e:
        logging.error(f"FAILURE: {user_role.upper()} login failed: {e}")
        return False

def test_invalid_login(user_role):
    logging.info(f"--- Test: Invalid Login for {user_role.upper()} (bad password) ---")
    original_password = CREDENTIALS[user_role]["password"]
    CREDENTIALS[user_role]["password"] = "wrongpassword123"

    # Clear any cached token for this role
    if user_role in USER_TOKENS:
        del USER_TOKENS[user_role]

    try:
        ApiClient(user_role=user_role) # This should attempt login and fail
        # If it doesn't raise an exception (which it should via response.raise_for_status()), it's a failure.
        logging.error(f"FAILURE: Invalid login for {user_role.upper()} did not raise an exception as expected.")
        assert False, "Invalid login should have failed"
        return False
    except requests.exceptions.HTTPError as e:
        assert e.response.status_code == 401, f"Expected 401 Unauthorized, got {e.response.status_code}"
        logging.info(f"SUCCESS: Invalid login for {user_role.upper()} correctly failed with 401 Unauthorized.")
        return True
    except Exception as e: # Catch other exceptions that might occur if ApiClient init changes
        logging.error(f"FAILURE: Invalid login for {user_role.upper()} failed with an unexpected error: {e}")
        return False
    finally:
        # Restore original password for subsequent tests
        CREDENTIALS[user_role]["password"] = original_password
        # Clear token again as it might have been (erroneously) set or login might be retried elsewhere
        if user_role in USER_TOKENS:
            del USER_TOKENS[user_role]


def test_invalid_username_login():
    logging.info(f"--- Test: Invalid Login (non-existent username) ---")
    user_role = "non_existent_user"
    # Temporarily add to CREDENTIALS for ApiClient structure, but it won't exist in DB
    CREDENTIALS[user_role] = {"username": "iamnotrealuser", "password": "anypassword"}

    if user_role in USER_TOKENS: # Should not be the case
        del USER_TOKENS[user_role]

    try:
        ApiClient(user_role=user_role)
        logging.error(f"FAILURE: Login with non-existent username did not raise an exception.")
        assert False, "Login with non-existent username should have failed"
        return False
    except requests.exceptions.HTTPError as e:
        assert e.response.status_code == 401, f"Expected 401 Unauthorized for non-existent user, got {e.response.status_code}"
        logging.info(f"SUCCESS: Login with non-existent username correctly failed with 401 Unauthorized.")
        return True
    except Exception as e:
        logging.error(f"FAILURE: Login with non-existent username failed with an unexpected error: {e}")
        return False
    finally:
        del CREDENTIALS[user_role] # Clean up temporary credential entry
        if user_role in USER_TOKENS: # Clean up token if any was created
            del USER_TOKENS[user_role]


def main():
    """Execute authentication API test scenarios.

    Returns
    -------
    bool
        True if all scenarios passed, False otherwise.
    """
    logging.info("======== Starting Authentication API Tests ========")

    results = {}

    # Test successful logins
    results["admin_login_success"] = test_successful_login("admin")
    results["vendor_login_success"] = test_successful_login("vendor")
    results["buyer_login_success"] = test_successful_login("buyer")

    # Test invalid logins (bad password)
    # Ensure tokens from successful logins are cleared before these tests for the same roles
    if "admin" in USER_TOKENS:
        del USER_TOKENS["admin"]
    results["admin_login_invalid_password"] = test_invalid_login("admin")

    if "vendor" in USER_TOKENS:
        del USER_TOKENS["vendor"]
    results["vendor_login_invalid_password"] = test_invalid_login("vendor")

    if "buyer" in USER_TOKENS:
        del USER_TOKENS["buyer"]
    results["buyer_login_invalid_password"] = test_invalid_login("buyer")

    # Test invalid login (non-existent username)
    results["non_existent_user_login_fail"] = test_invalid_username_login()

    logging.info("\n======== Authentication API Test Summary ========")
    all_passed = True
    for test_name, success in results.items():
        status = "PASSED" if success else "FAILED"
        logging.info(f"Test '{test_name}': {status}")
        if not success:
            all_passed = False

    if all_passed:
        logging.info("All authentication API tests passed!")
    else:
        logging.error("Some authentication API tests failed.")

    # Example of how to use the client for other tests later:
    # if results.get("admin_login_success"):
    #     admin_client = ApiClient(user_role="admin")  # Will use cached token
    #     # response = admin_client.get("/some_admin_endpoint/")
    #     # logging.info(f"Admin accessing endpoint: {response.status_code}")

    logging.info("======== Authentication API Tests Finished ========")
    return all_passed

if __name__ == "__main__":
    import sys
    passed = main()
    sys.exit(0 if passed else 1)
