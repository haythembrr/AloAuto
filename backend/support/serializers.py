from rest_framework import serializers
from .models import Ticket
from django.contrib.auth import get_user_model

User = get_user_model()

class TicketSerializer(serializers.ModelSerializer):
    # Use the status choices from the Ticket model
    status = serializers.ChoiceField(choices=Ticket.STATUS_CHOICES)

    user_email = serializers.EmailField(source='user.email', read_only=True)
    assigned_to_email = serializers.EmailField(source='assigned_to.email', read_only=True, allow_null=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'user',
            'user_email',
            'subject',
            'message',
            'status',
            'assigned_to',
            'assigned_to_email',
            'created_at',     # Was creation_date
            # 'updated_at',   # Not in current model
            'closed_at',      # Was closure_date
        ]
        read_only_fields = [
            'id',
            'created_at',
            # 'updated_at',
            'closed_at',
            'user_email',
            'assigned_to_email'
        ]
        extra_kwargs = {
            'user': {'write_only': True, 'required': False},
            'assigned_to': {'allow_null': True, 'required': False, 'queryset': User.objects.filter(is_staff=True)} # Ensure assigned_to is staff
        }

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        # Default status 'open' is set by the model
        # If status is provided, it will be used, otherwise model default.
        # To enforce 'open' on create via API:
        if 'status' not in validated_data:
            validated_data['status'] = 'open'
        return super().create(validated_data)
