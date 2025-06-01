from rest_framework import serializers
from .models import Return, OrderItem # Assuming OrderItem might be needed for validation or representation
# from backend.orders.serializers import OrderItemSerializer # For potential nested display - will mock if not available for now

# Mock OrderItemSerializer if not available, for planning purposes
class OrderItemSerializer(serializers.Serializer): # Basic mock
    id = serializers.IntegerField(read_only=True)
    # Add other fields you'd expect to see if it were the real serializer
    # For example: product_name = serializers.CharField(source='product.name', read_only=True)
    class Meta:
        fields = ['id'] # Mock fields


class ReturnRequestSerializer(serializers.ModelSerializer):
    # Use status choices from the model
    status = serializers.ChoiceField(choices=Return.RETURN_STATUS, required=False)
    # Use reason choices from the model for the 'reason' field
    reason = serializers.ChoiceField(choices=Return.RETURN_REASON)

    # For read-only, display details of the order_item
    # The 'source' argument points to the 'order_item' field on the Return model.
    order_item_details = OrderItemSerializer(source='order_item', read_only=True)

    # Expose order_id for write operations if Return model links directly to Order as well
    # For now, we assume 'order_item' is the primary link for creating a return.
    # The 'order' field on the Return model will be populated based on the 'order_item.order'.
    order = serializers.PrimaryKeyRelatedField(read_only=True) # Display order ID, derived from order_item

    class Meta:
        model = Return
        fields = [
            'id',
            'order', # Read-only, derived from order_item.order
            'order_item', # Writable: expects OrderItem ID
            'order_item_details', # Read-only nested representation
            'reason', # Categorized reason
            'description', # Detailed text reason
            'status',
            'created_at', # Was request_date
            'updated_at', # Can serve as resolution_date or last modification
            'refund_amount', # Was refunded_amount
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'order_item_details',
            'order', # Order is derived, not set directly
        ]

    def validate_order_item(self, value):
        # Ensure the user requesting the return is the one who bought the item.
        request = self.context.get('request')
        if request and hasattr(request, 'user') and not request.user.is_staff: # Allow staff to bypass for admin actions
            # Assuming 'user' field on Order model links to the customer
            if value.order.user != request.user:
                raise serializers.ValidationError("You can only request returns for your own order items.")
        return value

    def create(self, validated_data):
        # Set the direct 'order' FK on the Return instance from the 'order_item'
        validated_data['order'] = validated_data['order_item'].order

        # Ensure initial status is 'requested' if not provided
        if 'status' not in validated_data:
            validated_data['status'] = 'requested'
        return super().create(validated_data)

    def to_representation(self, instance):
        # Ensure the 'order' field is populated in the representation
        representation = super().to_representation(instance)
        representation['order'] = instance.order_item.order.id if instance.order_item else None
        return representation
