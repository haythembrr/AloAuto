from rest_framework import viewsets, permissions
from django.contrib.auth import get_user_model
from .models import Address
from .serializers import UserSerializer, AddressSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

    def perform_create(self, serializer):
        password = serializer.validated_data.pop('password', None)
        instance = serializer.save()
        if password:
            instance.set_password(password)
            instance.save()

    def perform_update(self, serializer):
        password = serializer.validated_data.pop('password', None)
        instance = serializer.save()
        if password:
            instance.set_password(password)
            instance.save()

class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        # If new address is set to default shipping, unset other default shipping addresses
        if serializer.validated_data.get('is_default_shipping'):
            Address.objects.filter(user=user, is_default_shipping=True).update(is_default_shipping=False)

        # If new address is set to default billing, unset other default billing addresses
        if serializer.validated_data.get('is_default_billing'):
            Address.objects.filter(user=user, is_default_billing=True).update(is_default_billing=False)

        serializer.save(user=user)

    def perform_update(self, serializer):
        instance = serializer.save()
        user = self.request.user

        # If updated address is set to default shipping, unset other default shipping addresses
        if instance.is_default_shipping:
            Address.objects.filter(user=user, is_default_shipping=True).exclude(pk=instance.pk).update(is_default_shipping=False)

        # If updated address is set to default billing, unset other default billing addresses
        if instance.is_default_billing:
            Address.objects.filter(user=user, is_default_billing=True).exclude(pk=instance.pk).update(is_default_billing=False)