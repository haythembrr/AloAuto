from django.db import models
from orders.models import Order

class Shipment(models.Model):
    SHIPMENT_STATUS = (
        ('pending', 'En attente'),
        ('in_transit', 'En transit'),
        ('delivered', 'Livré'),
        ('failed', 'Échoué')
    )

    order = models.OneToOneField(Order, on_delete=models.PROTECT, related_name='shipment')
    carrier = models.CharField(max_length=100)
    tracking_number = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=SHIPMENT_STATUS, default='pending')
    shipped_at = models.DateTimeField(null=True, blank=True)
    estimated_delivery = models.DateTimeField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Livraison'
        verbose_name_plural = 'Livraisons'