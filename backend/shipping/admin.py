from django.contrib import admin
from .models import Shipment
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone # For admin actions that might set dates

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_link',
        'carrier',
        'tracking_number',
        'status',
        'shipped_at',         # Was dispatch_date
        'estimated_delivery', # Was estimated_delivery_date
        # 'actual_delivery_date', # Not in current model
        'created_at',
        'updated_at',
    )
    list_filter = ('status', 'carrier', 'shipped_at', 'estimated_delivery') # Adjusted field names
    search_fields = ('order__id', 'tracking_number', 'carrier')
    readonly_fields = ('created_at', 'updated_at') # 'shipped_at' could be here if only set by logic

    def order_link(self, obj):
        if obj.order:
            try:
                link = reverse("admin:orders_order_change", args=[obj.order.id])
                return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
            except Exception: # Catch if reverse fails (e.g. orders app not namespaced correctly in admin)
                return f"Order #{obj.order.id} (Link error)"
        return "No order"
    order_link.short_description = 'Order'

    # Example admin action to update status
    def mark_as_shipped(self, request, queryset):
        for shipment in queryset:
            if shipment.status == 'pending': # Example: only mark pending shipments as shipped
                shipment.status = 'shipped' # Use actual status value from model choices
                if not shipment.shipped_at:
                    shipment.shipped_at = timezone.now()
                shipment.save()
    mark_as_shipped.short_description = "Mark selected shipments as Shipped"

    actions = [mark_as_shipped]
