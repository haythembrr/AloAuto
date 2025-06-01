from rest_framework import viewsets, permissions, status as http_status, parsers
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import ERPSyncLog, FileUploadLog
from .serializers import ERPSyncLogSerializer, FileUploadLogSerializer
from .tasks import process_uploaded_product_file_task
from django.core.files.storage import default_storage
from django.conf import settings # For MEDIA_ROOT (though default_storage abstracts this)
import os
import uuid
import logging # For logging within the view

logger = logging.getLogger(__name__)

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and \
               (request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'admin'))

class ERPSyncLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ERPSyncLog.objects.all().order_by('-timestamp')
    serializer_class = ERPSyncLogSerializer
    permission_classes = [IsAdminUser]

class FileUploadLogViewSet(viewsets.ModelViewSet):
    queryset = FileUploadLog.objects.all().order_by('-timestamp')
    serializer_class = FileUploadLogSerializer
    permission_classes = [IsAdminUser]
    # Define parser_classes at the class level if they apply to most actions,
    # or override per action if needed (as done for upload_product_file).
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    http_method_names = ['get', 'post', 'head', 'options', 'retrieve'] # Allow POST for custom action

    @action(detail=False, methods=['post'], url_path='upload-product-file',
            parser_classes=[parsers.MultiPartParser, parsers.FormParser]) # Specific parsers for this action
    def upload_product_file(self, request):
        file_obj = request.FILES.get('file')
        file_type_param = request.data.get('file_type', '').lower()

        if not file_obj:
            return Response({'error': 'File not provided.'}, status=http_status.HTTP_400_BAD_REQUEST)

        original_filename = file_obj.name
        file_extension = original_filename.split('.')[-1].lower() if '.' in original_filename else ''

        if not file_type_param:
            if file_extension == 'csv':
                file_type_param = 'csv'
            elif file_extension in ['xlsx', 'xls']:
                file_type_param = 'excel'
            else:
                 return Response({'error': 'File type not explicitly provided and could not be inferred (supported: csv, excel).'}, status=http_status.HTTP_400_BAD_REQUEST)

        if file_type_param not in [choice[0] for choice in FileUploadLog.FILE_TYPE_CHOICES]:
            return Response({'error': f'Unsupported file type: {file_type_param}. Supported: {[c[0] for c in FileUploadLog.FILE_TYPE_CHOICES]}'}, status=http_status.HTTP_400_BAD_REQUEST)

        # Path for saving: integrations/uploads/filename_with_uuid.ext
        # default_storage.save handles the MEDIA_ROOT internally.
        upload_subdir = os.path.join('integrations', 'uploads')
        unique_filename = f"{uuid.uuid4().hex}_{original_filename.replace(' ', '_')}" # Make filename more robust
        file_storage_path = os.path.join(upload_subdir, unique_filename)

        try:
            # The default_storage.save() method will create directories if they don't exist (for FileSystemStorage).
            saved_file_path = default_storage.save(file_storage_path, file_obj)
            logger.info(f"File uploaded by {request.user.username if request.user.is_authenticated else 'anonymous'} saved to: {saved_file_path}")
        except Exception as e:
            logger.error(f"File upload failed for {original_filename}. Error: {e}", exc_info=True)
            return Response({'error': f'Failed to save uploaded file: {str(e)}'}, status=http_status.HTTP_500_INTERNAL_SERVER_ERROR)

        upload_log = FileUploadLog.objects.create(
            original_file_name=original_filename,
            file_name=saved_file_path,
            file_type=file_type_param,
            status='uploaded',
            uploaded_by=request.user if request.user.is_authenticated else None
        )

        # Pass the path as saved by default_storage to the Celery task.
        # This path is typically relative to MEDIA_ROOT if using FileSystemStorage.
        # If using S3, it will be the S3 key.
        process_uploaded_product_file_task.delay(file_upload_log_id=upload_log.id, file_path=saved_file_path)

        serializer = FileUploadLogSerializer(upload_log, context={'request': request})
        return Response(serializer.data, status=http_status.HTTP_201_CREATED)

    def get_queryset(self):
        # This is already handled by permission_classes = [IsAdminUser] effectively,
        # but explicit filtering here is also fine if more complex non-admin views were ever added.
        if self.request.user and self.request.user.is_staff:
            return FileUploadLog.objects.all().order_by('-timestamp')
        # Non-admins should not see any by default if IsAdminUser is the only permission.
        # If other roles could see some logs, add logic here.
        return FileUploadLog.objects.none()

    # If you want to disable direct POST to create FileUploadLog (i.e., only allow via upload_product_file)
    # you can override the create method or rely on http_method_names if it excludes 'create'
    # Since 'post' is in http_method_names for the custom action, direct POST to /file-upload-logs/
    # would still call the standard create method of ModelViewSet if not overridden.
    # To prevent this, you could override create:
    def create(self, request, *args, **kwargs):
        return Response({'detail': 'Direct creation not allowed. Use the "upload-product-file" action.'},
                        status=http_status.HTTP_405_METHOD_NOT_ALLOWED)
