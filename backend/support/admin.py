from django.contrib import admin
from .models import Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'subject_summary',
        'user_display',
        'status',
        'assigned_to_display',
        'created_at',
        'closed_at'
    )
    list_filter = ('status', 'created_at', 'assigned_to')
    search_fields = ('subject', 'message', 'user__email', 'assigned_to__email') # Assumes User model has email

    # Make user and assigned_to read-only in the detail view if they are set through specific logic/defaults
    # 'user' is typically set on creation and not changed.
    # 'assigned_to' can be changed via list_editable or a custom action/form logic.
    readonly_fields = ('created_at', 'closed_at', 'user_display_readonly', 'assigned_to_display_readonly_detail')

    list_editable = ('status', 'assigned_to')

    fieldsets = (
        (None, {
            'fields': ('subject', 'message', 'user_display_readonly')
        }),
        ('Status & Assignment', {
            'fields': ('status', 'assigned_to', 'assigned_to_display_readonly_detail', 'closed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def user_display(self, obj): # For list_display
        return obj.user.email if obj.user else None
    user_display.short_description = 'User Email'

    def user_display_readonly(self, obj): # For fieldsets
        return obj.user.email if obj.user else 'N/A'
    user_display_readonly.short_description = 'Ticket User'

    def assigned_to_display(self, obj): # For list_display
        return obj.assigned_to.email if obj.assigned_to else None
    assigned_to_display.short_description = 'Assigned To (List)'

    def assigned_to_display_readonly_detail(self, obj): # For fieldsets
        return obj.assigned_to.email if obj.assigned_to else 'Not Assigned'
    assigned_to_display_readonly_detail.short_description = 'Currently Assigned To'

    def subject_summary(self, obj):
        return (obj.subject[:50] + '...') if len(obj.subject) > 50 else obj.subject
    subject_summary.short_description = 'Subject'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_to":
            # Filter the dropdown for 'assigned_to' to only show staff/admin users
            kwargs["queryset"] = User.objects.filter(is_staff=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
