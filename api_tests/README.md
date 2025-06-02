# E-commerce Django Application API Tests

This directory contains Python scripts designed to test the API endpoints of the e-commerce application. They use the `requests` library to make HTTP calls and verify responses.

## Prerequisites

1.  **Running Application**: The Django application server must be running.
2.  **Populated Database**: The database should be populated with test data. This can typically be done by running the Django management command:
    ```bash
    python manage.py populate_all_data
    ```
    This is crucial because the API tests rely on specific users and data being present (e.g., `admin_test_api_user`, `vendor_test_api_user`, products, categories, etc.). The `populate_accounts` command has been updated to create these specific users with a standard password (`password123`).
3.  **Python Environment**: Ensure Python 3 is installed.
4.  **Dependencies**: Install required Python packages from the project's main `requirements.txt` file. This includes `requests` and `Faker` (used by population scripts).
    ```bash
    pip install -r ../requirements.txt 
    # (Adjust path to requirements.txt if running from api_tests directory)
    # Or, if you have a separate requirements for tests: pip install -r requirements_tests.txt
    ```

## Configuration

### 1. Base API URL

The base URL for the API is configured in `api_tests/api_client.py`. By default, it is:
`BASE_URL = "http://localhost:8000/api"`

You can change this directly in the file or set the `API_BASE_URL` environment variable:
```bash
export API_BASE_URL="http://your-api-domain.com/api"
```

### 2. User Credentials for Testing

The test scripts use predefined user credentials which are expected to exist from the data population step. These are defined in `api_tests/api_client.py` in the `CREDENTIALS` dictionary:
- `admin_test_api_user`
- `vendor_test_api_user`
- `vendor2_test_api_user`
- `buyer_test_api_user`

All these users are expected to have the password `password123` (defined as `STANDARD_PASSWORD` in `api_client.py`). If the data population scripts change these credentials, `api_client.py` must be updated accordingly.

## Running the Tests

There are two ways to run the tests:

### 1. Running Individual Test Scripts

Each `test_*.py` file (e.g., `test_auth_api.py`, `test_accounts_api.py`) can be run directly from the command line from within the `api_tests` directory:

```bash
python test_auth_api.py
python test_accounts_api.py
# ... and so on for other test files
```
These scripts will output detailed logs of their execution, including requests made, responses received, and success/failure of assertions.

### 2. Using the Main Test Runner (`run_api_tests.py`)

A main test runner script `run_api_tests.py` is provided to execute all test suites in a predefined order.

All test scripts (`test_*.py`) have been structured with a `main()` function that encapsulates their execution logic and returns a status (True for success, False for failure). This allows them to be called by the runner.

To run all tests using the main runner:
```bash
python run_api_tests.py
```
The runner will execute each test module specified in its `TEST_MODULE_NAMES` list and provide an overall summary. It will exit with a status code 0 if all (called) suites pass, and 1 if any fail.

## Test Structure

-   **`api_client.py`**: A helper module that handles API authentication (JWT token retrieval) and provides an `ApiClient` class for making authenticated HTTP requests. It manages tokens for different user roles.
-   **`test_auth_api.py`**: Tests user login (valid and invalid credentials).
-   **`test_accounts_api.py`**: Tests user and address management functionalities for different roles.
-   **`test_vendors_api.py`**: Tests vendor profile management by vendors and admins.
-   **`test_catalogue_api.py`**: Tests public browsing of catalogue, admin management of categories, and vendor/admin management of products.
-   **`test_orders_api.py`**: Tests cart management, wishlist management, order creation by buyers, and order viewing/management by vendors and admins.
-   **`run_api_tests.py`**: The main script to run all test suites.

## Interpreting Output

Each test script, and the main runner, will output logs to the console. Look for:
-   `INFO` messages detailing the steps being performed.
-   `SUCCESS` or `FAILURE` indicators for specific assertions or scenarios.
-   `ERROR` messages if something unexpected occurs.

At the end of each script (and the main runner), a summary indicates overall pass/fail status.

## Extending Tests

To add more tests:
1.  Identify the relevant API endpoints and scenarios.
2.  Add new functions to the appropriate `test_*.py` file, or create a new test file for a new module.
3.  Use the `ApiClient` to make requests as the required user role.
4.  Add assertions for expected status codes and response data.
5.  If creating a new file, add it to the `TEST_MODULE_NAMES` list in `run_api_tests.py` and ensure it's refactored with a `main()` function.
