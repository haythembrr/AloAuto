import logging
import importlib
import os
import sys

# Add the parent directory (project root) to sys.path if api_client is there
# Or ensure api_tests is a package and use relative imports if structured differently.
# For now, assuming api_client.py is in the same directory or PYTHONPATH is set up.

# Configure basic logging for the runner
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [RUNNER] - %(message)s')

# List of test modules to run in order
# The order might matter if there are dependencies (e.g., auth tests should pass before others)
# or if later tests depend on data created/verified by earlier ones (though tests should aim for independence).
TEST_MODULE_NAMES = [
    "test_auth_api",
    "test_accounts_api",
    "test_vendors_api",
    "test_catalogue_api",
    "test_orders_api",
]

def run_test_module(module_name):
    """Imports and runs a test module's main execution block."""
    try:
        logging.info(f"--- Importing test module: {module_name} ---")
        module = importlib.import_module(module_name)

        # Assuming each test module has a main execution block like:
        # if __name__ == "__main__":
        #    # ... tests ...
        #    # Log summary and exit with code or return status
        #
        # To run it, we need to call a specific function or rely on its __main__ block.
        # A common pattern is to have a main() function in each test module.
        # Let's assume each module has a main() function that returns True on success, False on failure.

        if hasattr(module, "main") and callable(module.main):
            logging.info(f"--- Running main() for {module_name} ---")
            # Capture stdout/stderr or let it print directly.
            # For more sophisticated test runner, use unittest or pytest framework.
            # This is a simple sequential runner.
            module_passed = module.main() # Call the main function of the test module
            if module_passed is None: # If main() doesn't return, assume pass if no exception
                logging.warning(f"Test module {module_name} main() did not return explicit True/False. Assuming success if no exceptions.")
                return True
            return module_passed
        else:
            # Fallback: if no main(), try running its __main__ equivalent by re-triggering it.
            # This is a bit hacky. Better to define a callable entry point like main().
            # For now, we assume the `if __name__ == "__main__":` block in each test script
            # will run upon import if not guarded, or we modify them to have a main() func.
            # The current test scripts are structured with `if __name__ == "__main__":`
            # which means their tests run when executed directly, not just on import.
            # To make them runnable by this runner, they should encapsulate their logic in a function.

            # Let's modify the prompt for test scripts to have a `main()` function.
            # For now, I will assume the test scripts will be modified to have a `main()` function
            # that contains their `if __name__ == "__main__":` logic and returns True/False.
            logging.error(f"Test module {module_name} does not have a callable main() function. Cannot execute.")
            return False

    except ImportError as e:
        logging.error(f"Failed to import test module {module_name}: {e}")
        return False
    except Exception as e:
        logging.error(f"An error occurred while running test module {module_name}: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logging.info("========= Starting All API Test Suites =========")

    overall_summary = {}
    all_suites_passed = True

    for module_name in TEST_MODULE_NAMES:
        logging.info(f"\n>>> EXECUTING SUITE: {module_name} <<<\n")
        module_result = run_test_module(module_name)

        overall_summary[module_name] = module_result
        if not module_result:
            all_suites_passed = False
            logging.warning(f"Suite {module_name} reported failure. Subsequent tests might be affected.")

    logging.info("\n========= Overall API Test Execution Summary =========")
    for suite_name, passed in overall_summary.items():
        status = "PASSED" if passed else "FAILED"
        logging.info(f"Suite '{suite_name}': {status}")

    if all_suites_passed:
        logging.info("\nAll API test suites passed successfully!")
        sys.exit(0) # Exit with success code
    else:
        logging.error("\nSome API test suites failed.")
        sys.exit(1) # Exit with failure code

# Ensure each `test_*.py` file exposes a callable `main()` function that returns
# True when the tests pass and False otherwise. The runner imports each module
# and calls this function sequentially.
