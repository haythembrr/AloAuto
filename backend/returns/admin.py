from django.contrib import admin
from .models import Return # Assuming your model is named Return
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone # For admin actions if they set dates

@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_link_display',
        'order_item_id_display',
        'product_name_display',
        'status',
        'reason',
        'description_summary',
        'created_at',
        'updated_at',
        'refund_amount'
    )
    list_filter = ('status', 'reason', 'created_at')
    search_fields = (
        'order__id',
        'order_item__id',
        'order_item__product__name',
        'description'
    )
    readonly_fields = ('created_at', 'updated_at', 'order_link_display', 'order_item_id_display', 'product_name_display')
    list_editable = ('status', 'refund_amount') # Allow quick status & refund amount changes

    fieldsets = (
        (None, {
            'fields': ('order_link_display', 'order_item_id_display', 'product_name_display')
        }),
        ('Return Details', {
            'fields': ('reason', 'description')
        }),
        ('Status and Resolution', {
            'fields': ('status', 'refund_amount', 'created_at', 'updated_at')
        }),
    )

    def order_link_display(self, obj):
        if obj.order:
            try:
                link = reverse("admin:orders_order_change", args=[obj.order.id])
                return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
            except Exception:
                return f"Order #{obj.order.id} (Link error)"
        return "No Parent Order"
    order_link_display.short_description = 'Parent Order'

    def order_item_id_display(self, obj):
        if obj.order_item:
            # Link to OrderItem admin if OrderItem is registered
            # try:
            #     link = reverse("admin:orders_orderitem_change", args=[obj.order_item.id])
            #     return format_html('<a href="{}">Item ID: {}</a>', link, obj.order_item.id)
            # except Exception:
            # return f"Item ID: {obj.order_item.id} (No admin link)"
            return f"Item ID: {obj.order_item.id}" # Simpler display without direct link for now
        return "N/A"
    order_item_id_display.short_description = 'Order Item ID'

    def product_name_display(self, obj):
        if obj.order_item and hasattr(obj.order_item, 'product') and obj.order_item.product:
            return obj.order_item.product.name
        return "N/A"
    product_name_display.short_description = 'Product'

    def description_summary(self, obj):
        if obj.description:
            return (obj.description[:75] + '...') if len(obj.description) > 75 else obj.description
        return ""
    description_summary.short_description = 'Description Summary'

    def approve_selected_returns(self, request, queryset):
        queryset.filter(status='requested').update(status='approved', updated_at=timezone.now())
    approve_selected_returns.short_description = "Mark selected returns as Approved"

    def reject_selected_returns(self, request, queryset):
        queryset.filter(status='requested').update(status='rejected', updated_at=timezone.now())
    reject_selected_returns.short_description = "Mark selected returns as Rejected"

    actions = [approve_selected_returns, reject_selected_returns]
