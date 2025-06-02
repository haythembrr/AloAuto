import requests
import json
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000/api")
STANDARD_PASSWORD = "password123" # Used during data population

# Predefined user credentials (can be expanded or loaded from config)
# These usernames are based on the populate_accounts.py script's logic
# It's assumed that the first few users of each type are somewhat predictable,
# or we fetch them by predictable usernames if they were created as such.
# For a more robust solution, the populate scripts could output some key user details.

# Let's assume the populate_accounts script creates users like:
# admin_testuser1, vendor_testuser1, buyer_testuser1
# For simplicity, we'll use generic usernames here and assume they exist with STANDARD_PASSWORD.
# In a real scenario, these should be specific and guaranteed by data generation.

CREDENTIALS = {
    "admin": {"username": "admin_test_api_user", "password": STANDARD_PASSWORD},
    "vendor": {"username": "vendor_test_api_user", "password": STANDARD_PASSWORD},
    "buyer": {"username": "buyer_test_api_user", "password": STANDARD_PASSWORD},
    # For specific tests, we might need more users, e.g., a second vendor
    "vendor2": {"username": "vendor2_test_api_user", "password": STANDARD_PASSWORD},
}

# To store fetched tokens
USER_TOKENS = {}

def login(user_role="admin"):
    """Logs in a user and stores the token."""
    if user_role in USER_TOKENS:
        logging.info(f"Token for {user_role} already available.")
        return USER_TOKENS[user_role]

    creds = CREDENTIALS.get(user_role)
    if not creds:
        logging.error(f"Credentials not found for role: {user_role}")
        raise ValueError(f"Credentials not found for role: {user_role}")

    try:
        endpoint = f"{BASE_URL}/token/"
        logging.info(f"Attempting login for {user_role} ({creds['username']}) at {endpoint}")
        response = requests.post(endpoint, data={"username": creds["username"], "password": creds["password"]})
        response.raise_for_status()
        token = response.json().get("access")
        if not token:
            logging.error(f"Login failed for {user_role}: 'access' token not found in response.")
            raise ValueError("Access token not found in login response.")
        USER_TOKENS[user_role] = token
        logging.info(f"Login successful for {user_role}. Token obtained.")
        return token
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP error during login for {user_role} ({creds['username']}): {e.response.status_code} - {e.response.text}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error during login for {user_role}: {e}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred during login for {user_role}: {e}")
        raise


class ApiClient:
    def __init__(self, user_role="guest"):
        self.base_url = BASE_URL
        self.token = None
        self.user_role = user_role

        if user_role != "guest":
            try:
                self.token = login(user_role)
            except Exception as e:
                # Error already logged in login function
                logging.warning(f"Could not automatically log in user {user_role}. Client will be unauthenticated.")
                self.user_role = "guest" # Fallback to guest

    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def request(self, method, endpoint, data=None, params=None, log_payload=True):
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        payload_for_log = data if log_payload else "Payload not logged for this request."
        logging.info(f"[{self.user_role.upper()}] Making {method} request to {url} with params {params}, data: {payload_for_log}")

        try:
            if data is not None and not isinstance(data, (str, bytes)):
                data = json.dumps(data) # Ensure data is JSON string if it's a dict/list

            response = requests.request(method, url, headers=headers, data=data, params=params)
            
            # Attempt to log JSON response, or text if not JSON
            try:
                response_json = response.json()
                logging.info(f"Response: {response.status_code} - {json.dumps(response_json, indent=2)}")
            except ValueError: # Not JSON
                logging.info(f"Response: {response.status_code} - {response.text[:200]}...") # Log first 200 chars

            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Request failed: {e}")
            # Return a mock response or re-raise depending on desired handling
            mock_response = requests.Response()
            mock_response.status_code = 503 # Service Unavailable
            mock_response.reason = str(e)
            return mock_response


    def get(self, endpoint, params=None):
        return self.request("GET", endpoint, params=params)

    def post(self, endpoint, data=None, log_payload=True):
        return self.request("POST", endpoint, data=data, log_payload=log_payload)

    def put(self, endpoint, data=None, log_payload=True):
        return self.request("PUT", endpoint, data=data, log_payload=log_payload)

    def patch(self, endpoint, data=None, log_payload=True):
        return self.request("PATCH", endpoint, data=data, log_payload=log_payload)

    def delete(self, endpoint):
        return self.request("DELETE", endpoint)

if __name__ == "__main__":
    # Example usage / basic test of the client
    logging.info("Testing ApiClient...")
    
    # Test Guest
    guest_client = ApiClient(user_role="guest")
    logging.info("Guest client attempting to access a public endpoint (e.g., products list)")
    # response = guest_client.get("/catalogue/products/") # Assuming this is a public endpoint
    # logging.info(f"Guest client response status: {response.status_code}")

    # Test Admin
    try:
        admin_client = ApiClient(user_role="admin")
        if admin_client.token:
            logging.info("Admin client authenticated.")
            # response = admin_client.get("/accounts/users/") # Example protected endpoint
            # logging.info(f"Admin client GET /accounts/users/ status: {response.status_code}")
        else:
            logging.warning("Admin client could not authenticate. Check credentials and API availability.")
    except Exception as e:
        logging.error(f"Failed to initialize admin client: {e}")

    # Test Vendor
    try:
        vendor_client = ApiClient(user_role="vendor")
        if vendor_client.token:
            logging.info("Vendor client authenticated.")
        else:
            logging.warning("Vendor client could not authenticate.")
    except Exception as e:
        logging.error(f"Failed to initialize vendor client: {e}")

    # Test Buyer
    try:
        buyer_client = ApiClient(user_role="buyer")
        if buyer_client.token:
            logging.info("Buyer client authenticated.")
        else:
            logging.warning("Buyer client could not authenticate.")
    except Exception as e:
        logging.error(f"Failed to initialize buyer client: {e}")

    logging.info("ApiClient test finished.")
