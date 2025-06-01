from rest_framework import serializers
from .models import Cart, CartItem, Order, OrderItem, Wishlist
from catalogue.serializers import ProductSerializer

class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_id = serializers.IntegerField(write_only=True)
    total_price = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        read_only=True
    )

    class Meta:
        model = CartItem
        fields = ['id', 'cart', 'product', 'product_id', 'quantity', 'total_price']
        read_only_fields = ['cart']

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Cart
        fields = ['id', 'items', 'total', 'created_at', 'updated_at']

class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    # price_at_purchase = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) # Ensure it's read-only after creation

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'order', # Added to explicitly show it, usually handled by relation
            'product',
            'quantity',
            'unit_price',      # Original field
            'price_at_purchase', # New field
            'total_price'
        ]
        read_only_fields = ['product', 'unit_price', 'price_at_purchase', 'total_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'status', 'total_amount', 'shipping_address',
            'payment_method', 'items', 'notes', 'created_at'
        ]
        read_only_fields = ['status', 'total_amount']

class WishlistSerializer(serializers.ModelSerializer):
    products = ProductSerializer(many=True, read_only=True)
    
    class Meta:
        model = Wishlist
        fields = ['id', 'products', 'created_at']