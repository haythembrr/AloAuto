from django.contrib import admin
from .models import Product, Category, ProductImage

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'image')
    list_filter = ('parent',)
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1 # Number of empty forms to display
    readonly_fields = ('created_at',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'vendor', 'price', 'stock_quantity', 'is_active', 'attributes_summary', 'updated_at')
    list_filter = ('category', 'vendor', 'is_active', 'updated_at')
    search_fields = ('name', 'description', 'vendor__company_name', 'category__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'vendor', 'category', 'description')
        }),
        ('Pricing, Stock & Status', { # Combined for brevity
            'fields': ('price', 'stock_quantity', 'is_active')
        }),
        ('Attributes', {
            'fields': ('attributes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def attributes_summary(self, obj):
        if isinstance(obj.attributes, dict):
            return f"{len(obj.attributes)} attributes"
        elif obj.attributes: # If it's not a dict but not None (e.g. stored as string by mistake)
            return "Invalid data"
        return "None"
    attributes_summary.short_description = 'Attributes'
    ordering = ('-updated_at',)

# Basic admin for ProductImage if needed to be managed separately (optional)
# @admin.register(ProductImage)
# class ProductImageAdmin(admin.ModelAdmin):
#     list_display = ('product_name', 'image', 'is_primary', 'created_at')
#     list_filter = ('is_primary', 'created_at')
#     search_fields = ('product__name',)
#     readonly_fields = ('created_at',)

#     def product_name(self, obj):
#         return obj.product.name
#     product_name.short_description = 'Product'
