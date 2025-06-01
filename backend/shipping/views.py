from rest_framework import viewsets, permissions, status as http_status
from .models import Shipment
from .serializers import ShipmentSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone # Added for setting dates in custom action

# Basic permission checks (simplified for this implementation)
# More specific permissions like IsVendorOwner would be needed for production.
class IsAdminOrActionSpecific(permissions.BasePermission):
    """
    Allows admin full access.
    For non-admins, allows access only to specific safe actions or if they are vendor for certain actions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or (hasattr(user, 'role') and user.role == 'admin'):
            return True # Admin can do anything

        if view.action in ['list', 'retrieve']:
            return True # Authenticated users can list/retrieve (queryset will filter)

        if view.action in ['update_shipment_status', 'partial_update', 'update']:
            # In a real scenario, check if user is vendor for THIS shipment's order
            # For now, this is a simplified check.
            # This should ideally be an object-level permission.
            return hasattr(user, 'vendorprofile') or (hasattr(user, 'role') and user.role == 'vendor')

        if view.action == 'create': # Assuming vendors or admins can create
             return hasattr(user, 'vendorprofile') or (hasattr(user, 'role') and user.role == 'vendor')

        return False # Deny other actions like destroy for non-admins


class ShipmentViewSet(viewsets.ModelViewSet):
    queryset = Shipment.objects.all()
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrActionSpecific]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Shipment.objects.none()

        if hasattr(user, 'role') and user.role == 'admin':
            return Shipment.objects.all()
        if user.is_staff:
            return Shipment.objects.all()

        # Buyers see shipments for their own orders
        buyer_qs = Shipment.objects.filter(order__user=user)

        # Vendors see shipments for orders containing their products
        if hasattr(user, 'role') and user.role == 'vendor':
            # This requires related_name 'items' on Order model pointing to OrderItem,
            # and Product model on OrderItem, and Vendor model on Product.
            # Example: order__items__product__vendor__user=user
            # For this placeholder, we'll assume a direct link or a simplified logic.
            # If a user is a vendor, they might see shipments associated with orders they vended.
            # This part needs a robust implementation based on actual model relations.
            # A common pattern:
            # vendor_qs = Shipment.objects.filter(order__items__product__vendor__user=user).distinct()
            # return buyer_qs | vendor_qs # Combine querysets if a user can be both
            # For now, returning buyer_qs; vendor specific logic needs careful model traversal.
            # If using the simplified 'vendorprofile' check from prompt:
            if hasattr(user, 'vendorprofile'):
                 # This is still not correct for filtering shipments *related* to vendor's sales.
                 # Placeholder: a vendor needs a more specific query.
                 # To avoid data leakage, if not admin, only show buyer's perspective for now.
                 pass # Let it fall through to buyer_qs or an empty set if not a buyer for any order.

        return buyer_qs.distinct() # Ensure distinct if combining querysets later

    def perform_create(self, serializer):
        # Admins or Vendors (associated with the order) should be able to create.
        # The permission class IsAdminOrActionSpecific handles the 'create' action.
        # Ensure order is part of validated_data and links correctly.
        # Further validation: check if request.user (if vendor) is allowed to create shipment for this order.
        serializer.save()

    @action(detail=True, methods=['post']) # Permissions handled by IsAdminOrActionSpecific
    def update_shipment_status(self, request, pk=None):
        shipment = self.get_object()
        # Object-level permission check should ideally happen here or in permission_classes
        # e.g. self.check_object_permissions(request, shipment)

        new_status = request.data.get('status')

        if not new_status:
            return Response({'error': 'Status not provided'}, status=http_status.HTTP_400_BAD_REQUEST)

        valid_statuses = [choice[0] for choice in Shipment.SHIPMENT_STATUS]
        if new_status not in valid_statuses:
            return Response({'error': f'Invalid status. Valid statuses are: {", ".join(valid_statuses)}'}, status=http_status.HTTP_400_BAD_REQUEST)

        # Check if user is allowed to set this status (e.g. only admin can set 'failed_delivery')
        # Check if user is vendor for this order, or admin
        is_admin = request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'admin')
        is_related_vendor = False # Placeholder for actual check
        if hasattr(request.user, 'role') and request.user.role == 'vendor':
            # Simplified check: does this order contain any product from this vendor?
            if shipment.order.items.filter(product__vendor__user=request.user).exists():
                 is_related_vendor = True

        if not (is_admin or is_related_vendor):
            return Response({'error': 'You do not have permission to update this shipment.'}, status=http_status.HTTP_403_FORBIDDEN)

        if new_status == 'shipped' and not shipment.shipped_at:
            shipment.shipped_at = timezone.now()
        # Add actual_delivery_date logic if/when that field is added to the model
        # elif new_status == 'delivered' and (not shipment.actual_delivery_date): # Assuming you add actual_delivery_date
        #     shipment.actual_delivery_date = timezone.now()

        shipment.status = new_status
        shipment.save()
        return Response(ShipmentSerializer(shipment).data, status=http_status.HTTP_200_OK)
