from django.contrib import admin
from .models import Log
import json # For pretty printing JSON in details_summary

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user_email_display', 'action', 'ip_address', 'details_summary') # Renamed timestamp to created_at
    list_filter = ('action', 'created_at', 'user__email') # Renamed timestamp to created_at
    search_fields = ('user__email', 'action', 'ip_address', 'details__icontains') # Django 3.1+ for JSONField icontains

    # Make all fields read-only in the admin detail view as logs are immutable
    readonly_fields = ('created_at', 'user_display_for_detail', 'action', 'ip_address', 'formatted_details')

    fieldsets = (
        (None, {
            'fields': ('created_at', 'user_display_for_detail', 'action', 'ip_address')
        }),
        ('Details', {
            'fields': ('formatted_details',),
        }),
    )

    def user_email_display(self, obj): # For list_display
        if obj.user:
            return obj.user.email if hasattr(obj.user, 'email') and obj.user.email else str(obj.user)
        return 'Anonymous/System'
    user_email_display.short_description = 'User'
    user_email_display.admin_order_field = 'user__email' # Allows sorting by email

    def user_display_for_detail(self, obj): # For readonly_fields in detail view
        if obj.user:
            return obj.user.email if hasattr(obj.user, 'email') and obj.user.email else str(obj.user)
        return 'Anonymous/System'
    user_display_for_detail.short_description = 'User'


    def details_summary(self, obj): # For list_display
        try:
            if isinstance(obj.details, dict):
                # Show a few key-value pairs or a count
                summary_items = [f"{k}: {v}" for k, v in list(obj.details.items())[:2]] # Show first 2 items
                summary = "; ".join(summary_items)
                if len(obj.details) > 2:
                    summary += "..."
            elif isinstance(obj.details, str) and obj.details.startswith('{') and obj.details.endswith('}'):
                # Attempt to parse if it looks like a JSON string
                parsed_details = json.loads(obj.details)
                summary_items = [f"{k}: {v}" for k, v in list(parsed_details.items())[:2]]
                summary = "; ".join(summary_items)
                if len(parsed_details) > 2:
                    summary += "..."
            else:
                summary = str(obj.details)
            return (summary[:75] + '...') if len(summary) > 75 else summary
        except (json.JSONDecodeError, TypeError):
            return str(obj.details)[:75] + ('...' if len(str(obj.details)) > 75 else '')
    details_summary.short_description = 'Details (Summary)'

    def formatted_details(self, obj): # For detail view (readonly_fields)
        from django.utils.html import format_html
        try:
            if isinstance(obj.details, dict):
                pretty_json = json.dumps(obj.details, indent=2, ensure_ascii=False)
            elif isinstance(obj.details, str) and obj.details.startswith('{') and obj.details.endswith('}'):
                pretty_json = json.dumps(json.loads(obj.details), indent=2, ensure_ascii=False)
            else:
                pretty_json = str(obj.details)
            return format_html("<pre>{}</pre>", pretty_json)
        except (json.JSONDecodeError, TypeError):
            return str(obj.details)
    formatted_details.short_description = 'Details'

    def has_add_permission(self, request):
        # Logs should not be manually added via admin
        return False

    def has_change_permission(self, request, obj=None):
        # Logs should be immutable
        return False

    def has_delete_permission(self, request, obj=None):
        # Allow deletion only by superusers for maintenance
        return request.user.is_superuser

    ordering = ('-created_at',) # Display newest logs first
