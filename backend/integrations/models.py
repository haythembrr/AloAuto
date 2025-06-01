from django.db import models
from django.conf import settings

class ERPSyncLog(models.Model):
    SYNC_TYPE_CHOICES = [
        ('product_catalog', 'Product Catalog Sync'),
        ('order_export', 'Order Export'),
        ('stock_update', 'Stock Update'),
        # Add other types as needed
    ]
    STATUS_CHOICES = [
        ('started', 'Started'),
        ('in_progress', 'In Progress'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial_success', 'Partial Success'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    sync_type = models.CharField(max_length=50, choices=SYNC_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    message = models.TextField(blank=True, null=True, help_text="Summary message, e.g., errors or success count.")
    details = models.JSONField(null=True, blank=True, default=dict, help_text="Richer context, e.g., specific error details, processed IDs.")
    # Optional: Link to a user who initiated it, if applicable
    # initiated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='erp_sync_logs')

    class Meta:
        verbose_name = "ERP Sync Log"
        verbose_name_plural = "ERP Sync Logs"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_sync_type_display()} at {self.timestamp.strftime('%Y-%m-%d %H:%M')} - {self.get_status_display()}"


class FileUploadLog(models.Model):
    FILE_TYPE_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel (XLSX)'),
        # Add other types as needed
    ]
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('validating', 'Validating'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed_validation', 'Failed Validation'),
        ('failed_processing', 'Failed Processing'),
    ]

    timestamp = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255, help_text="Stored file name/path after upload.")
    original_file_name = models.CharField(max_length=255, help_text="Original name of the uploaded file.")
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')

    processed_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(null=True, blank=True, default=list, help_text="List of errors, e.g., {'row': 5, 'error': 'Invalid SKU'}.") # Default changed to list
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='file_uploads')

    class Meta:
        verbose_name = "File Upload Log"
        verbose_name_plural = "File Upload Logs"
        ordering = ['-timestamp']

    def __str__(self):
        user_str = str(self.uploaded_by) if self.uploaded_by else "Unknown user"
        return f"{self.original_file_name} ({self.get_file_type_display()}) uploaded at {self.timestamp.strftime('%Y-%m-%d %H:%M')} by {user_str} - {self.get_status_display()}"
