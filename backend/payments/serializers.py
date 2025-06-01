from rest_framework import serializers
from .models import Payment

class PaymentSerializer(serializers.ModelSerializer):
    # Use the choices defined in the Payment model directly
    status = serializers.ChoiceField(choices=Payment.PAYMENT_STATUS)
    method = serializers.ChoiceField(choices=Payment.PAYMENT_METHOD)

    # The 'order' field will be represented by its PrimaryKeyRelatedField by default.
    # This is usually fine. If a more detailed representation of the order is needed,
    # OrderSerializer could be used (read_only=True) or order_id could be exposed directly.

    class Meta:
        model = Payment
        fields = [
            'id',
            'order',
            'amount', # Changed from amount_paid to match model
            'method',
            'status',
            'transaction_id', # Changed from transaction_reference
            'created_at',     # Changed from payment_date
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
