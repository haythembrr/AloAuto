from rest_framework import viewsets, permissions, status as http_status
from .models import Ticket
from .serializers import TicketSerializer
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.contrib.auth import get_user_model # Use get_user_model

User = get_user_model()

# Permissions
class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and \
               (request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'admin'))

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or (hasattr(request.user, 'role') and request.user.role == 'admin'):
            return True
        return obj.user == request.user

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer

    def get_permissions(self):
        if self.action == 'assign':
            return [IsAdmin()]
        # IsOwnerOrAdmin will apply to retrieve, update, partial_update, destroy (if not overridden)
        # For 'list' and 'create', IsAuthenticated is sufficient as queryset/perform_create handle ownership.
        if self.action in ['list', 'create']:
            return [permissions.IsAuthenticated()]
        return [IsOwnerOrAdmin()] # Default for retrieve, update, destroy, custom actions unless overridden


    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Ticket.objects.none()
        if user.is_staff or (hasattr(user, 'role') and user.role == 'admin'):
            return Ticket.objects.all().order_by('-created_at')
        return Ticket.objects.filter(user=user).order_by('-created_at')

    def perform_create(self, serializer):
        # User is automatically set in serializer create method using request.user
        serializer.save()

    def perform_update(self, serializer):
        instance = serializer.instance
        new_status = serializer.validated_data.get('status', instance.status)

        # Model status choices: ('open', 'Ouvert'), ('pending', 'En attente'), ('closed', 'Fermé')
        if new_status == 'closed' and not instance.closed_at:
            serializer.save(closed_at=timezone.now())
        elif new_status != 'closed' and instance.closed_at: # If status changes from closed to something else
            serializer.save(closed_at=None) # Re-opening a ticket, clear closed_at
        else:
            serializer.save()

    @action(detail=True, methods=['post']) # Permissions handled by get_permissions -> IsAdmin
    def assign(self, request, pk=None):
        ticket = self.get_object() # Object permission check from IsOwnerOrAdmin will run
                                  # But get_permissions for 'assign' action specifies IsAdmin
        admin_user_id = request.data.get('admin_user_id')
        if admin_user_id is None:
            return Response({'error': 'admin_user_id not provided in request data.'}, status=http_status.HTTP_400_BAD_REQUEST)
        try:
            # Ensure the user being assigned is actually staff/admin
            admin_user = User.objects.get(id=admin_user_id, is_staff=True) # or check role == 'admin'
            ticket.assigned_to = admin_user
            ticket.save()
            # Pass context to serializer if it needs request (e.g. for HyperlinkedRelatedField)
            return Response(TicketSerializer(ticket, context={'request': request}).data)
        except User.DoesNotExist:
            return Response({'error': 'Admin user not found or user is not an admin.'}, status=http_status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=http_status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post']) # Permissions handled by get_permissions -> IsOwnerOrAdmin
    def close(self, request, pk=None):
        ticket = self.get_object() # Object permission check from IsOwnerOrAdmin will run

        if ticket.status == 'closed' and ticket.closed_at:
            return Response({'error': 'Ticket is already closed.'}, status=http_status.HTTP_400_BAD_REQUEST)

        ticket.status = 'closed'
        ticket.closed_at = timezone.now()
        ticket.save()
        return Response(TicketSerializer(ticket, context={'request': request}).data)
