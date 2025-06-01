from rest_framework import viewsets, permissions, status as http_status
from .models import Return
from .serializers import ReturnRequestSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
# Assuming User model might be needed for role checks if not using is_staff directly
# from backend.accounts.models import User

# Custom Permissions
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and (request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'admin'))

class IsOwnerOrAdminOrRelatedVendor(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        if user.is_staff or (hasattr(user, 'role') and user.role == 'admin'):
            return True

        # Owner of the return request (buyer who made the order for the item)
        if obj.order_item.order.user == user:
            return True

        # Vendor who owns the product in the order_item
        if hasattr(user, 'role') and user.role == 'vendor':
            # This assumes: obj (Return) -> order_item (OrderItem) -> product (Product) -> vendor (Vendor) -> user (User)
            # Make sure the path `obj.order_item.product.vendor.user` correctly points to the vendor's user account.
            # It might be `obj.order_item.product.vendor.user_account` or similar depending on your Vendor model.
            # For this example, I'll assume `obj.order_item.product.vendor.user` is correct.
            if hasattr(obj.order_item.product, 'vendor') and obj.order_item.product.vendor and hasattr(obj.order_item.product.vendor, 'user'):
                 if obj.order_item.product.vendor.user == user:
                    return True
        return False


class ReturnRequestViewSet(viewsets.ModelViewSet):
    queryset = Return.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Return.objects.none()

        if user.is_staff or (hasattr(user, 'role') and user.role == 'admin'):
            return Return.objects.all()

        # Buyer sees their own return requests
        buyer_qs = Return.objects.filter(order_item__order__user=user)

        vendor_qs = Return.objects.none()
        if hasattr(user, 'role') and user.role == 'vendor':
            # Vendor sees return requests for items they sold.
            vendor_qs = Return.objects.filter(order_item__product__vendor__user=user)

        return (buyer_qs | vendor_qs).distinct()

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()] # Only authenticated users can create
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()] # Authenticated users can list/retrieve (filtered by queryset)
        if self.action in ['update', 'partial_update', 'approve', 'reject']:
            return [IsOwnerOrAdminOrRelatedVendor()] # Owner (buyer for some fields), Vendor (for status), Admin
        if self.action == 'process_refund':
            return [IsAdmin()] # Only Admin for this
        if self.action == 'destroy':
            return [IsAdmin()] # Only Admin can delete

        return super().get_permissions()

    def perform_create(self, serializer):
        # Serializer's validate_order_item checks ownership for non-staff users.
        # Serializer's create method sets initial status and links order.
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdminOrRelatedVendor])
    def approve(self, request, pk=None):
        return_request = self.get_object()
        user = request.user

        # Check if user is admin or the vendor of this item
        is_admin = user.is_staff or (hasattr(user, 'role') and user.role == 'admin')
        is_item_vendor = False
        if hasattr(user, 'role') and user.role == 'vendor':
            if hasattr(return_request.order_item.product, 'vendor') and return_request.order_item.product.vendor and hasattr(return_request.order_item.product.vendor, 'user'):
                if return_request.order_item.product.vendor.user == user:
                    is_item_vendor = True

        if not (is_admin or is_item_vendor):
            return Response({'error': 'You do not have permission to approve this return.'}, status=http_status.HTTP_403_FORBIDDEN)

        if return_request.status == 'requested':
            return_request.status = 'approved'
            # resolution_date is not in model, using updated_at implicitly by model's auto_now=True
            return_request.save()
            return Response(ReturnRequestSerializer(return_request, context={'request': request}).data)
        return Response({'error': 'Return request must be in "requested" state to approve.'}, status=http_status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsOwnerOrAdminOrRelatedVendor])
    def reject(self, request, pk=None):
        return_request = self.get_object()
        user = request.user
        is_admin = user.is_staff or (hasattr(user, 'role') and user.role == 'admin')
        is_item_vendor = False
        if hasattr(user, 'role') and user.role == 'vendor':
            if hasattr(return_request.order_item.product, 'vendor') and return_request.order_item.product.vendor and hasattr(return_request.order_item.product.vendor, 'user'):
                 if return_request.order_item.product.vendor.user == user:
                    is_item_vendor = True

        if not (is_admin or is_item_vendor):
            return Response({'error': 'You do not have permission to reject this return.'}, status=http_status.HTTP_403_FORBIDDEN)

        if return_request.status == 'requested':
            return_request.status = 'rejected'
            return_request.save()
            return Response(ReturnRequestSerializer(return_request, context={'request': request}).data)
        return Response({'error': 'Return request must be in "requested" state to reject.'}, status=http_status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def process_refund(self, request, pk=None):
        return_request = self.get_object()
        if return_request.status == 'approved':
            return_request.status = 'refunded'
            if return_request.refund_amount is None:
                # This needs to be robust: consider discounts, taxes, shipping costs for the item.
                # For now, simplified to unit_price * quantity from OrderItem.
                # OrderItem model must have 'unit_price' and 'quantity' fields.
                if hasattr(return_request.order_item, 'unit_price') and hasattr(return_request.order_item, 'quantity'):
                    return_request.refund_amount = return_request.order_item.unit_price * return_request.order_item.quantity
                else: # Fallback if OrderItem doesn't have these fields, or set to 0 to indicate manual check needed
                    return_request.refund_amount = 0

            # resolution_date not in model, updated_at will be set by auto_now=True
            return_request.save()
            # TODO: Trigger actual refund via payment gateway, adjust stock, notify user.
            return Response(ReturnRequestSerializer(return_request, context={'request': request}).data)
        return Response({'error': 'Return request must be "approved" to process refund.'}, status=http_status.HTTP_400_BAD_REQUEST)
