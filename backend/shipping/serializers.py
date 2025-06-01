from rest_framework import serializers
from .models import Shipment

class ShipmentSerializer(serializers.ModelSerializer):
    # Use the choices defined in the Shipment model directly for the status field
    status = serializers.ChoiceField(choices=Shipment.SHIPMENT_STATUS)

    # The 'order' field will be represented by its PrimaryKeyRelatedField by default.
    class Meta:
        model = Shipment
        fields = [
            'id',
            'order',
            'carrier',
            'tracking_number',
            'status',
            'shipped_at',         # Was dispatch_date in plan
            'estimated_delivery', # Was estimated_delivery_date in plan
            # 'actual_delivery_date', # Not in current model, omitting for now
            'created_at',         # Added from model
            'updated_at',         # Added from model
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
