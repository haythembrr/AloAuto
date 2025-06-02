# AloAuto E-commerce Platform - Testing Utilities

This document provides an overview of the testing utilities available in this project, including data generation scripts and API test scripts.

## 1. Prerequisites

*   **Python**: Python 3.8+ is recommended.
*   **Dependencies**: Install all project dependencies from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
*   **Django Project Setup**:
    *   Ensure your Django project is configured correctly (database settings, secret key, etc.).
    *   Run database migrations before populating data:
        ```bash
        python backend/manage.py migrate
        ```

## 2. Data Generation

The project includes Django management commands to populate the database with a large amount of realistic test data. This is essential for creating a development environment that mirrors production complexity and for providing a consistent dataset for API testing.

### Command to Run

To populate all data for all relevant apps, run the main population command from the `backend/` directory (where `manage.py` is located):

```bash
python backend/manage.py populate_all_data
```

This command will call individual population scripts for each app (accounts, catalogue, orders, etc.) in the correct order of dependency.

### `--clear` Option

If you want to remove existing data from the tables before populating, you can use the `--clear` option:

```bash
python backend/manage.py populate_all_data --clear
```

**Caution**: The `--clear` option will delete data from most application tables. By default, it does **not** delete `User` records to prevent accidental deletion of superuser accounts. If a full reset including users is needed, manual deletion or a more specific script would be required.

### Test User Accounts

The data population scripts (specifically `populate_accounts`) create a set of predefined user accounts that are essential for running the API tests. These users are created with a standard password.

**Standard Password for Test Users**: `password123`

**Key Test User Accounts:**

*   **Admin User**:
    *   Username: `admin_test_api_user`
    *   Email: `admintest@example.com`
*   **Vendor Users**:
    *   Username: `vendor_test_api_user`
    *   Email: `vendortest@example.com`
    *   Username: `vendor2_test_api_user` (a second vendor for specific scenarios)
    *   Email: `vendor2test@example.com`
*   **Buyer User**:
    *   Username: `buyer_test_api_user`
    *   Email: `buyertest@example.com`

These users, along with others (approx. 1000 users total, ~100 vendors), are created by the `populate_all_data` command.

## 3. API Test Execution

A suite of API tests is available in the `api_tests/` directory. These scripts use Python and the `requests` library to perform HTTP calls against the application's API endpoints, simulating various user scenarios.

### Detailed API Test README

For detailed information on configuring and running the API tests, including prerequisites specific to the API tests, refer to the README located within the API tests directory:
[`api_tests/README.md`](api_tests/README.md)

### Quick Command to Run All API Tests

To execute all API test suites using the main test runner script, navigate to the project root directory and run:

```bash
python api_tests/run_api_tests.py
```

This script will run tests for authentication, accounts, vendors, catalogue, and orders in sequence. Ensure the Django development server is running and the database is populated before executing these tests.

## 4. Recommended Workflow for Testing

1.  **Initial Project Setup**:
    *   Clone the repository.
    *   Set up your Python environment and install dependencies (`pip install -r requirements.txt`).
    *   Configure your Django settings (e.g., database in `backend/aloauto/settings.py`).
    *   Run database migrations: `python backend/manage.py migrate`.

2.  **Populate Test Data**:
    *   Run the data generation command: `python backend/manage.py populate_all_data`.
    *   Use `--clear` if you need to start with a fresh set of test data.

3.  **Run API Tests**:
    *   Ensure the Django development server is running: `python backend/manage.py runserver`.
    *   Execute the API tests: `python api_tests/run_api_tests.py`.
    *   Review the output logs for any failures or errors. Consult `api_tests/README.md` for more details on individual test execution or troubleshooting.

This workflow ensures that your development and testing environment is consistently set up with necessary data before API tests are performed.
