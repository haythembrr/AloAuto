from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ERPSyncLogViewSet, FileUploadLogViewSet

router = DefaultRouter()
router.register(r'erp-sync-logs', ERPSyncLogViewSet, basename='erpsynclog')
router.register(r'file-uploads', FileUploadLogViewSet, basename='fileuploadlog')
# The custom action 'upload_product_file' will be available at
# /api/integrations/file-uploads/upload-product-file/ (if base path is /api/integrations/)

urlpatterns = [
    path('', include(router.urls)),
]
