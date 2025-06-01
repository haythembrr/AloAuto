from django.contrib import admin
from .models import Payment
from django.urls import reverse
from django.utils.html import format_html

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order_link',
        'amount', # Changed from amount_paid
        'method',
        'status',
        'created_at', # Changed from payment_date
        'transaction_id', # Changed from transaction_reference
        'updated_at'
    )
    list_filter = ('status', 'method', 'created_at') # Changed from payment_date
    search_fields = ('order__id', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at') # payment_date changed to created_at

    def order_link(self, obj):
        if obj.order:
            # Ensure your order app is 'orders' and model name is 'order'
            # This will work if the Order model is registered with the admin site
            # under the 'orders' app and 'order' model name.
            try:
                link = reverse("admin:orders_order_change", args=[obj.order.id])
                return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
            except Exception: # Catch if reverse fails for any reason
                return f"Order #{obj.order.id} (Link error)"
        return "No order"
    order_link.short_description = 'Order'

    # Optional: Add actions, like marking as paid or refunded, directly in admin
    # def mark_paid(self, request, queryset):
    #     queryset.update(status='paid')
    # mark_paid.short_description = "Mark selected payments as Paid"

    # def mark_refunded(self, request, queryset):
    #     queryset.update(status='refunded')
    # mark_refunded.short_description = "Mark selected payments as Refunded"

    # actions = [mark_paid, mark_refunded]
