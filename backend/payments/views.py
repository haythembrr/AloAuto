from rest_framework import viewsets, permissions, status # Added status for Response
from .models import Payment
from .serializers import PaymentSerializer
from rest_framework.response import Response # For custom actions
from rest_framework.decorators import action # For custom actions

# Using Django's IsAdminUser for staff check
# from rest_framework.permissions import IsAdminUser # This could be used directly

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated] # Default to IsAuthenticated

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Payment.objects.none()

        # Admin/staff can see all payments
        # Assumes 'role' attribute exists on user model as per previous analysis:
        # User model: role = models.CharField(max_length=10, choices=ROLES, default='buyer')
        # ROLES = ( ('buyer', 'Acheteur'), ('vendor', 'Vendeur'), ('admin', 'Administrateur'),)
        if hasattr(user, 'role') and user.role == 'admin':
            return Payment.objects.all()
        elif user.is_staff: # Fallback for Django's default staff users
             return Payment.objects.all()

        # Buyer can see payments for their own orders
        # Assumes Payment.order.user is the buyer
        return Payment.objects.filter(order__user=user)

    def get_permissions(self):
        user = self.request.user
        # Admin users have full permissions for any action
        if hasattr(user, 'role') and user.role == 'admin':
            return [permissions.IsAdminUser()] # IsAdminUser checks for is_staff
        elif user.is_staff: # Fallback for Django's default staff users
            return [permissions.IsAdminUser()]

        # Authenticated non-admin (e.g., buyer) users:
        if self.action in ['list', 'retrieve']: # Buyers can list/retrieve their payments
            return [permissions.IsAuthenticated()]

        # For other actions like 'create', 'update', 'partial_update', 'destroy',
        # and custom actions not specifically decorated, deny by default for non-admins.
        # Payments are typically created via the order process, not directly by users.
        # Direct modification by non-admins is also generally not allowed.
        return [permissions.IsAdminUser()] # Default to admin for other actions

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser]) # Restricted to admin/staff
    def mark_as_refunded(self, request, pk=None):
        payment = self.get_object()
        if payment.status == 'paid': # Using model's status value
            payment.status = 'refunded' # Using model's status value
            payment.save()
            serializer = self.get_serializer(payment) # Return the updated payment object
            return Response(serializer.data, status=status.HTTP_200_OK) # Added OK status
        else:
            return Response({'error': 'Only paid payments can be refunded.'}, status=status.HTTP_400_BAD_REQUEST)
