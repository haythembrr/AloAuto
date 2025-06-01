from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet

router = DefaultRouter()
router.register(r'', PaymentViewSet, basename='payment') # Registering at root of payments/

urlpatterns = [
    path('', include(router.urls)),
]
