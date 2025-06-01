from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import VendorViewSet

router = DefaultRouter()
router.register(r'', VendorViewSet, basename='vendor')

urlpatterns = [
    path('', include(router.urls)),
]