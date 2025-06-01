from celery import shared_task
from .models import ERPSyncLog, FileUploadLog
from backend.catalogue.models import Product # Assuming Product model path
import pandas as pd
import io
from django.core.files.storage import default_storage
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_erp_products_task(self, erp_system_name="DefaultERP"):
    sync_log_entry = ERPSyncLog.objects.create(
        sync_type=f'product_catalog_{erp_system_name.lower()}', # Use f-string correctly
        status='started',
        message=f'Starting product catalog sync from {erp_system_name}.'
    )
    logger.info(f"Task ID: {self.request.id} - Starting ERP product sync for {erp_system_name}, Log ID: {sync_log_entry.id}")
    try:
        # Placeholder for actual ERP integration logic
        # Example: erp_client = ERPClient(erp_system_name)
        # products_data = erp_client.fetch_products()
        import time
        time.sleep(5) # Simulate network delay or processing time

        # Simulated data processing
        simulated_erp_products_count = 5 # Assume 5 products fetched from ERP
        updated_count = 0
        created_count = 0

        # for prod_data in products_data:
        #     product, created = Product.objects.update_or_create(
        #         sku=prod_data.get('sku'), # Assuming SKU is a unique identifier
        #         defaults={
        #             'name': prod_data.get('name'),
        #             'price': prod_data.get('price'),
        #             'stock_quantity': prod_data.get('stock_quantity'),
        #             # ... other fields ...
        #         }
        #     )
        #     if created:
        #         created_count += 1
        #     else:
        #         updated_count += 1

        # For this placeholder, we just simulate success
        created_count = 2 # Simulated
        updated_count = 3 # Simulated

        sync_log_entry.status = 'success'
        sync_log_entry.message = (
            f"Successfully synced {simulated_erp_products_count} products from {erp_system_name}. "
            f"{created_count} created, {updated_count} updated."
        )
        logger.info(f"Task ID: {self.request.id} - ERP product sync successful for {erp_system_name}.")
    except Exception as e:
        logger.error(f"Task ID: {self.request.id} - Error during ERP product sync for {erp_system_name}: {e}", exc_info=True)
        sync_log_entry.status = 'failed'
        sync_log_entry.message = f"Error during sync: {e}"
        # self.retry(exc=e) # Optional: use Celery's retry mechanism
        raise # Re-raise the exception if not using Celery's retry or want it to be marked as failed immediately
    finally:
        sync_log_entry.save()
    return sync_log_entry.message

@shared_task(bind=True, max_retries=3, default_retry_delay=120) # Increased retry delay
def process_uploaded_product_file_task(self, file_upload_log_id, file_content_str=None, file_path=None):
    try:
        upload_log_entry = FileUploadLog.objects.get(id=file_upload_log_id)
    except FileUploadLog.DoesNotExist:
        logger.error(f"Task ID: {self.request.id} - FileUploadLog with ID {file_upload_log_id} not found.")
        return f"FileUploadLog with ID {file_upload_log_id} not found. Task cannot proceed." # Added more informative return

    upload_log_entry.status = 'processing'
    upload_log_entry.save()
    logger.info(f"Task ID: {self.request.id} - Starting processing for file: {upload_log_entry.original_file_name}, Log ID: {upload_log_entry.id}")

    processed_count = 0
    error_count = 0
    error_list = []

    try:
        if not file_content_str and not file_path:
            raise ValueError("Either file_content_str or file_path must be provided for processing.")

        file_like_obj = None # Define to ensure it's in scope for finally block
        if file_content_str:
            file_like_obj = io.StringIO(file_content_str)
        elif file_path: # Ensure file_path is not None or empty
            if not default_storage.exists(file_path):
                raise FileNotFoundError(f"File not found at path: {file_path}")
            file_like_obj = default_storage.open(file_path, 'r') # Assuming text mode for CSV

        if upload_log_entry.file_type == 'csv':
            try:
                # Assuming CSV has headers: sku, name, description, price, stock_quantity, category_slug, vendor_id
                # This is a placeholder; actual column names and mapping logic would be more complex.
                df = pd.read_csv(file_like_obj)
                required_columns = {'sku', 'price', 'stock_quantity'} # Simplified required columns
                if not required_columns.issubset(df.columns):
                    raise ValueError(f"CSV missing required columns. Found: {list(df.columns)}, Required minimum: {list(required_columns)}")

                for index, row in df.iterrows():
                    try:
                        sku = str(row['sku']).strip()
                        if not sku:
                            raise ValueError("SKU cannot be empty.")

                        # Placeholder: Find or create product by SKU
                        # product, created = Product.objects.update_or_create(
                        #     sku=sku, # Assuming Product model has an SKU field
                        #     defaults={
                        #         'name': row.get('name', f"Product {sku}"), # Default name if not provided
                        #         'description': row.get('description', ''),
                        #         'price': float(row['price']),
                        #         'stock_quantity': int(row['stock_quantity']),
                        #         # 'category': Category.objects.get(slug=row.get('category_slug')), # Requires Category model
                        #         # 'vendor': Vendor.objects.get(id=row.get('vendor_id')),       # Requires Vendor model
                        #     }
                        # )
                        logger.debug(f"Processing row {index+1}: SKU {sku}, Price {row['price']}, Stock {row['stock_quantity']}")
                        processed_count += 1
                    except Exception as row_e:
                        error_count += 1
                        error_list.append({'row': index + 2, 'error': str(row_e), 'data': row.to_dict()})
                        logger.warning(f"Task ID: {self.request.id} - Error processing row {index + 2} of {upload_log_entry.original_file_name}: {row_e}")
            except Exception as pd_e:
                raise ValueError(f"Error parsing CSV file: {pd_e}") # This will be caught by the outer try-except

        elif upload_log_entry.file_type == 'excel':
            # Placeholder for Excel processing
            # df = pd.read_excel(file_like_obj, engine='openpyxl')
            # Similar processing logic as CSV...
            raise NotImplementedError("Excel processing not fully implemented in this placeholder task.")
        else:
            raise ValueError(f"Unsupported file type: {upload_log_entry.file_type}")

        if error_count > 0:
            upload_log_entry.status = 'failed_processing' # Or 'partial_success' if some rows succeeded
        else:
            upload_log_entry.status = 'completed'

        upload_log_entry.message = f"Processed file {upload_log_entry.original_file_name}. {processed_count} rows processed, {error_count} errors."
        logger.info(f"Task ID: {self.request.id} - Finished processing for file: {upload_log_entry.original_file_name}. Status: {upload_log_entry.status}")

    except FileNotFoundError as fnf_e:
        logger.error(f"Task ID: {self.request.id} - File not found for FileUploadLog ID {file_upload_log_id}: {fnf_e}", exc_info=True)
        upload_log_entry.status = 'failed_processing'
        upload_log_entry.message = f"File not found: {fnf_e}"
    except NotImplementedError as ni_e:
        logger.error(f"Task ID: {self.request.id} - Functionality not implemented for FileUploadLog ID {file_upload_log_id}: {ni_e}", exc_info=True)
        upload_log_entry.status = 'failed_processing'
        upload_log_entry.message = str(ni_e)
    except Exception as e:
        logger.error(f"Task ID: {self.request.id} - Error processing FileUploadLog ID {file_upload_log_id}: {e}", exc_info=True)
        upload_log_entry.status = 'failed_processing' # General failure
        upload_log_entry.message = f"General error during processing: {e}"
        # self.retry(exc=e) # Optional: use Celery's retry mechanism
    finally:
        if file_path and file_like_obj: # Ensure file_like_obj was opened before trying to close
            try:
                file_like_obj.close()
                # Optionally delete the file from storage if it's temporary
                # default_storage.delete(file_path)
                # logger.info(f"Task ID: {self.request.id} - Closed and deleted temporary file: {file_path}")
            except Exception as close_e:
                logger.error(f"Task ID: {self.request.id} - Error closing/deleting file {file_path}: {close_e}")

        upload_log_entry.processed_rows = processed_count
        upload_log_entry.error_rows = error_count
        upload_log_entry.error_details = error_list # Save errors
        upload_log_entry.save()

    return upload_log_entry.message
