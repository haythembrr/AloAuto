from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from integrations.models import ERPSyncLog, FileUploadLog # Assuming these models exist
from accounts.models import User # For user who uploaded file
import random

class Command(BaseCommand):
    help = 'Populates the database with sample integration logs (ERP Sync, File Uploads)'

    def handle(self, *args, **options):
        fake = Faker()
        admin_users = list(User.objects.filter(is_staff=True))

        # Populate ERPSyncLog
        self.stdout.write("Creating ERPSyncLog entries...")
        num_erp_logs = random.randint(50, 100)
        erp_sync_logs_created = 0
        
        sync_types = ['product_update', 'order_export', 'inventory_sync', 'customer_import']
        sync_statuses = ['success', 'failed', 'partial_success', 'pending']

        for _ in range(num_erp_logs):
            sync_time = fake.date_time_between(start_date="-6m", end_date="now", tzinfo=timezone.get_current_timezone())
            status = random.choice(sync_statuses)
            
            details = {}
            if status == 'failed':
                details['error_message'] = fake.sentence()
                details['error_code'] = fake.random_int(min=100, max=599)
            elif status == 'partial_success':
                details['items_synced'] = random.randint(50, 1000)
                details['items_failed'] = random.randint(1, 50)
            else: # success or pending
                details['items_processed'] = random.randint(100, 2000)

            try:
                ERPSyncLog.objects.create(
                    sync_type=random.choice(sync_types),
                    status=status,
                    records_affected=details.get('items_processed') or details.get('items_synced', 0),
                    run_time=sync_time,
                    log_details=details # Assuming this is a JSONField or TextField
                )
                erp_sync_logs_created +=1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating ERPSyncLog: {e}"))

        self.stdout.write(self.style.SUCCESS(f'Successfully created {erp_sync_logs_created} ERPSyncLog entries.'))

        # Populate FileUploadLog
        self.stdout.write("Creating FileUploadLog entries...")
        if not admin_users:
            self.stdout.write(self.style.WARNING('No admin/staff users found. FileUploadLogs will not be associated with a user.'))
        
        num_file_logs = random.randint(20, 30)
        file_upload_logs_created = 0
        file_types = ['product_import_csv', 'vendor_data_xls', 'image_zip_archive', 'customer_list_csv']
        file_statuses = ['uploaded', 'processing', 'completed', 'failed']

        for _ in range(num_file_logs):
            upload_time = fake.date_time_between(start_date="-3m", end_date="now", tzinfo=timezone.get_current_timezone())
            status = random.choice(file_statuses)
            
            file_name = f"{fake.word()}_{fake.random_int(min=100,max=999)}.{random.choice(['csv','xls','zip','jpg'])}"
            
            log_details = {}
            if status == 'failed':
                log_details['error'] = fake.sentence()
            elif status == 'completed':
                log_details['rows_processed'] = random.randint(10,500)
            
            try:
                FileUploadLog.objects.create(
                    file_name=file_name,
                    file_type=random.choice(file_types),
                    uploaded_by=random.choice(admin_users) if admin_users else None,
                    upload_time=upload_time,
                    status=status,
                    processing_details=log_details # Assuming JSONField or TextField
                )
                file_upload_logs_created += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating FileUploadLog: {e}"))


        self.stdout.write(self.style.SUCCESS(f'Successfully created {file_upload_logs_created} FileUploadLog entries.'))
        self.stdout.write(self.style.SUCCESS('Successfully populated integration logs.'))
