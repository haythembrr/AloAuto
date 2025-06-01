from rest_framework import serializers
from .models import ERPSyncLog, FileUploadLog

class ERPSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ERPSyncLog
        fields = '__all__' # Or list specific fields for more control
        read_only_fields = ('timestamp', 'status', 'message', 'details') # Usually these are set by the task

class FileUploadLogSerializer(serializers.ModelSerializer):
    # This serializer is mainly for displaying log entries.
    # File upload itself is handled by a custom action in the ViewSet.
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True, allow_null=True)

    class Meta:
        model = FileUploadLog
        fields = [
            'id',
            'timestamp',
            'file_name',
            'original_file_name',
            'file_type',
            'status',
            'processed_rows',
            'error_rows',
            'error_details',
            'uploaded_by', # FK to user, write_only for perform_create if needed, but set in view
            'uploaded_by_email', # Read-only display
        ]
        read_only_fields = (
            'id',
            'timestamp',
            'file_name', # Set by the view upon saving the file
            'status',
            'processed_rows',
            'error_rows',
            'error_details',
            'uploaded_by_email' # This is derived
        )
        extra_kwargs = {
            'uploaded_by': {'write_only': True, 'required': False, 'allow_null': True}, # Set implicitly by view
        }
