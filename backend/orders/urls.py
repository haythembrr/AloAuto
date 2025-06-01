from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CartViewSet, OrderViewSet, WishlistViewSet

router = DefaultRouter()
router.register(r'carts', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'wishlists', WishlistViewSet, basename='wishlist')

urlpatterns = [
    path('', include(router.urls)),
]