from rest_framework import serializers
from .models import Category, Product, ProductImage

class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'alt_text', 'is_primary', 'created_at']
        read_only_fields = ['created_at']

class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'description', 'image', 'children', 'created_at', 'updated_at']
        read_only_fields = ['slug', 'created_at', 'updated_at']

    def get_children(self, obj):
        # Avoid recursion if obj has no children or to prevent potential infinite loops if data is bad
        if not obj.children.exists():
            return []
        return CategorySerializer(obj.children.all(), many=True).data

class ProductSerializer(serializers.ModelSerializer):
    vendor_name = serializers.CharField(source='vendor.company_name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'vendor', 'vendor_name', 'category', 'category_name',
            'name', 'slug', 'sku', 'description', 'price', 'stock_quantity',
            'attributes', 'weight', 'dimensions', 'is_active', 'images',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'vendor', 'vendor_name', 'category_name', 'slug',
            'images', 'created_at', 'updated_at'
        ]