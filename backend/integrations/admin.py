from django.contrib import admin
from .models import ERPSyncLog, FileUploadLog
import json
from django.utils.html import format_html

@admin.register(ERPSyncLog)
class ERPSyncLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'sync_type', 'status', 'message_summary')
    list_filter = ('sync_type', 'status', 'timestamp')
    search_fields = ('sync_type', 'message', 'details__icontains') # For searching in JSONField
    readonly_fields = ('timestamp', 'sync_type', 'status', 'message', 'details_pretty')

    def message_summary(self, obj):
        if obj.message:
            return (obj.message[:75] + '...') if len(obj.message) > 75 else obj.message
        return None # Explicitly return None if no message
    message_summary.short_description = 'Message'

    def details_pretty(self, obj):
        if obj.details:
            # Convert dict to pretty formatted JSON string
            pretty_json = json.dumps(obj.details, indent=2, ensure_ascii=False) # Changed indent to 2 for less space
            return format_html("<pre>{}</pre>", pretty_json)
        return "-"
    details_pretty.short_description = 'Details (Formatted)'

    fieldsets = (
        (None, {'fields': ('timestamp', 'sync_type', 'status', 'message')}),
        ('Formatted Details', {'fields': ('details_pretty',), 'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False # Allow only superuser to delete if needed via has_delete_permission

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser # Only superusers can delete logs


@admin.register(FileUploadLog)
class FileUploadLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'original_file_name', 'file_type', 'status', 'uploaded_by_display', 'processed_rows', 'error_rows')
    list_filter = ('file_type', 'status', 'timestamp', 'uploaded_by__email') # Filter by email
    search_fields = ('original_file_name', 'file_name', 'uploaded_by__email', 'error_details__icontains')
    readonly_fields = ('timestamp', 'file_name', 'original_file_name', 'file_type', 'status',
                       'processed_rows', 'error_rows', 'error_details_pretty', 'uploaded_by_display_detail')

    def uploaded_by_display(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by and hasattr(obj.uploaded_by, 'email') else (str(obj.uploaded_by) if obj.uploaded_by else None)
    uploaded_by_display.short_description = 'Uploaded By'
    uploaded_by_display.admin_order_field = 'uploaded_by__email'

    def uploaded_by_display_detail(self, obj):
        return obj.uploaded_by.email if obj.uploaded_by and hasattr(obj.uploaded_by, 'email') else (str(obj.uploaded_by) if obj.uploaded_by else 'N/A')
    uploaded_by_display_detail.short_description = 'Uploaded By User'

    def error_details_pretty(self, obj):
        if obj.error_details: # error_details is a list of dicts
            # Convert list of dicts to pretty formatted JSON string
            pretty_json = json.dumps(obj.error_details, indent=2, ensure_ascii=False) # Changed indent to 2
            return format_html("<pre>{}</pre>", pretty_json)
        return "-"
    error_details_pretty.short_description = 'Error Details (Formatted)'

    fieldsets = (
        (None, {'fields': ('timestamp', 'original_file_name', 'file_name', 'file_type', 'status', 'uploaded_by_display_detail')}),
        ('Processing Stats', {'fields': ('processed_rows', 'error_rows')}),
        ('Formatted Error Details', {'fields': ('error_details_pretty',), 'classes': ('collapse',)}),
    )

    def has_add_permission(self, request):
        return False # Logs are created by system/uploads, not manually in admin

    def has_change_permission(self, request, obj=None):
        return False # Log entries should be immutable

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser # Only superusers can delete logs
