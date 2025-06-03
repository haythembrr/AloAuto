from rest_framework import permissions

class IsVendorOwner(permissions.BasePermission):
    """
    Custom permission to only allow owners of a vendor object to edit it.
    Assumes the view's queryset is for the Vendor model or that get_object() returns a Vendor instance.
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Admin users have all permissions for write operations as well
        if request.user and hasattr(request.user, 'role') and request.user.role == 'admin':
            return True

        # Write permissions are only allowed to the user associated with the vendor for non-admins.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False
