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

        # Write permissions are only allowed to the user associated with the vendor.
        # Assumes the Vendor model 'obj' has a 'user' ForeignKey field.
        # Adjust 'user' to the actual field name on your Vendor model that links to the User model.
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # If the vendor object itself is the user (e.g. for a Vendor profile that is a User proxy model)
        # elif isinstance(obj, request.user.__class__): # Check if obj is a User instance
        #     return obj == request.user
        return False
