from django.contrib import admin
from .models import Order, OrderItem, Cart, CartItem, Wishlist

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    fields = ('product', 'quantity', 'unit_price', 'price_at_purchase', 'total_price')
    readonly_fields = ('product', 'unit_price', 'price_at_purchase', 'total_price', 'created_at')
    extra = 0
    can_delete = False # Usually, order items are not deleted directly from an order

    def get_queryset(self, request):
        # Optimize query to prefetch related product if needed, though not strictly necessary for readonly_fields display
        return super().get_queryset(request).select_related('product')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_display', 'status', 'total_amount', 'created_at', 'payment_method')
    list_filter = ('status', 'created_at', 'payment_method')
    search_fields = ('id', 'user__email', 'shipping_address__street', 'items__product__name')
    readonly_fields = ('user', 'total_amount', 'created_at', 'updated_at', 'shipping_address', 'payment_method', 'notes') # Make more fields readonly for existing orders
    inlines = [OrderItemInline]

    fieldsets = (
        (None, {'fields': ('user', 'status')}), # User might be better as readonly_fields if not changeable
        ('Order Details', {'fields': ('total_amount', 'payment_method', 'shipping_address', 'notes')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )
    ordering = ('-created_at',)

    def user_display(self, obj):
        return obj.user.email if obj.user else None # Or str(obj.user)
    user_display.short_description = 'User'

    # If you want to allow changing status or other fields for existing orders, remove them from readonly_fields
    # and ensure they are in fieldsets if not using default layout.
    # For example, to make status editable:
    # readonly_fields = ('user', 'total_amount', 'created_at', 'updated_at', ...)
    # fieldsets = ( (None, {'fields': ('user', ('status', 'payment_method'))}), ... )
    # And remove 'status' from readonly_fields.


# Optional: Direct admin for OrderItem if needed (usually managed via Order inline)
# @admin.register(OrderItem)
# class OrderItemAdmin(admin.ModelAdmin):
#     list_display = ('id', 'order_link', 'product_name', 'quantity', 'unit_price', 'price_at_purchase', 'total_price', 'created_at')
#     readonly_fields = ('order', 'product', 'unit_price', 'price_at_purchase', 'total_price', 'created_at')
#     search_fields = ('order__id', 'product__name')
#     list_filter = ('created_at',)

#     def order_link(self, obj):
#         from django.urls import reverse
#         from django.utils.html import format_html
#         link = reverse("admin:orders_order_change", args=[obj.order.id])
#         return format_html('<a href="{}">Order #{}</a>', link, obj.order.id)
#     order_link.short_description = 'Order'

#     def product_name(self, obj):
#         return obj.product.name
#     product_name.short_description = 'Product'


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity', 'created_at')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    filter_horizontal = ('products',)
    readonly_fields = ('created_at', 'updated_at')
