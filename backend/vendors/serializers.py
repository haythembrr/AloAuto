from rest_framework import serializers
from .models import Vendor

class VendorSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = Vendor
        fields = [
            'id', 'user', 'user_email', 'user_name', 'company_name', 'slug',
            'description', 'contact_email', 'contact_phone', 'address', 'website',
            'tax_number', 'status', 'bank_info', 'logo', 'registration_date',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['user', 'status', 'slug', 'created_at', 'updated_at']