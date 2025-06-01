from django.contrib.auth.signals import user_logged_in, user_logged_out # user_logged_out is not directly used by log_user_logout based on connect
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.apps import apps # For robust model importing
from .models import Log

# Using apps.get_model to avoid direct import issues during app loading.
# This is generally safer for signals.

# Define a function to get models to avoid calling apps.get_model at module level before apps are fully ready,
# though for signals connected in AppConfig.ready(), it should be fine.
# However, best practice is to get them inside the functions or once apps are loaded.

def get_order_model():
    return apps.get_model('orders', 'Order')

def get_product_model():
    return apps.get_model('catalogue', 'Product')

def get_user_model():
    return apps.get_model(settings.AUTH_USER_MODEL.split('.')[0], settings.AUTH_USER_MODEL.split('.')[1])


def get_request_ip(request_obj): # Renamed request to request_obj to avoid conflict with request module
    if request_obj:
        x_forwarded_for = request_obj.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request_obj.META.get('REMOTE_ADDR')
        return ip
    return None

def log_action(user_obj, action_description, details_dict=None, ip_address=None): # Renamed user to user_obj
    Log.objects.create(
        user=user_obj if user_obj and user_obj.is_authenticated else None,
        action=action_description,
        details=details_dict if details_dict is not None else {},
        ip_address=ip_address
    )

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs): # 'request' and 'user' are standard args for this signal
    ip = get_request_ip(request)
    log_action(user, "User logged in", ip_address=ip)

# The user_logged_out signal also provides 'request' and 'user'
@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    ip = get_request_ip(request)
    # User might be None if session was destroyed before logout signal, or if not fully authenticated
    # log_action will handle user if None or not authenticated
    log_action(user, "User logged out", ip_address=ip)

@receiver(post_save, sender='orders.Order') # Use string reference for sender
def log_order_change(sender, instance, created, **kwargs):
    # For post_save signals, 'request' is not available directly.
    # IP address and the acting user (if not instance.user) would need to be passed via other means
    # or logged at the view level if specific to a request.
    # Here, we log based on the order's user.
    acting_user = instance.user if hasattr(instance, 'user') else None
    action = "Order created" if created else f"Order status updated to {instance.status}"
    details = {
        'order_id': instance.id,
        'status': instance.status,
        # Ensure total_amount is serializable (e.g., convert Decimal to float/str if necessary for JSON)
        'total_amount': float(instance.total_amount) if hasattr(instance, 'total_amount') and instance.total_amount is not None else None,
        'user_id': acting_user.id if acting_user else None
    }
    log_action(acting_user, action, details) # IP address will be None

# Removed the duplicate definition that used sender=Product directly.
# The following definition correctly uses the string reference.
@receiver(post_save, sender='catalogue.Product') # Use string reference for sender
def log_product_change(sender, instance, created, **kwargs):
    # Similar to Order, 'request' isn't available here.
    # Determining the user who made the change is tricky from post_save if not explicitly passed.
    # If product is changed via admin, admin user is implicit. If via API by vendor, need that context.
    # A common pattern is to use middleware to store the current user in thread-locals (use with caution)
    # or to log such actions directly in the ViewSets.
    # For now, we assume the vendor associated with product is relevant, or it's a system change.

    # Try to get user from vendor relationship. This is an assumption.
    # Path could be instance.vendor.user or instance.vendor.user_account etc.
    # Based on catalogue/models.py: Product.vendor -> vendors.models.Vendor
    # Based on vendors/models.py: Vendor.user -> settings.AUTH_USER_MODEL
    acting_user = None
    if hasattr(instance, 'vendor') and instance.vendor and hasattr(instance.vendor, 'user'):
        acting_user = instance.vendor.user

    action = "Product created" if created else "Product updated"
    details = {
        'product_id': instance.id,
        'product_name': instance.name,
        'vendor_id': instance.vendor.id if hasattr(instance, 'vendor') and instance.vendor else None,
        'changed_by_user_id': acting_user.id if acting_user else None
    }
    # If acting_user is None, this means the change might have been done by an admin not directly linked as product's vendor,
    # or by the system. This log entry will have user=None.
    log_action(acting_user, action, details) # IP address will be None
