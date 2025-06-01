from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Vendor
from .serializers import VendorSerializer
from .permissions import IsVendorOwner

class VendorViewSet(viewsets.ModelViewSet):
    serializer_class = VendorSerializer
    permission_classes = [permissions.IsAuthenticated, IsVendorOwner]

    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Vendor.objects.all()
        return Vendor.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        vendor = self.get_object()
        if request.user.role != 'admin':
            return Response(
                {'error': 'Not authorized'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        vendor.status = 'active'
        vendor.save()
        return Response({'status': 'vendor activated'})