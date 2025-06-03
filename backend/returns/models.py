from django.db import models
from django.conf import settings # Make sure this is imported
from orders.models import Order, OrderItem

class Return(models.Model):
    RETURN_STATUS = (
        ('requested', 'Demandé'),
        ('approved', 'Approuvé'),
        ('rejected', 'Rejeté'),
        ('refunded', 'Remboursé')
    )

    RETURN_REASON = (
        ('defective', 'Défectueux'),
        ('wrong_item', 'Mauvais article'),
        ('not_satisfied', 'Non satisfait'),
        ('other', 'Autre')
    )

    order = models.ForeignKey(Order, on_delete=models.PROTECT, related_name='returns')
    order_item = models.ForeignKey(OrderItem, on_delete=models.PROTECT, related_name='returns')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='returns_requested')
    reason = models.CharField(max_length=20, choices=RETURN_REASON)
    status = models.CharField(max_length=20, choices=RETURN_STATUS, default='requested')
    description = models.TextField()
    quantity_returned = models.PositiveIntegerField(null=True, blank=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    requested_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Retour'
        verbose_name_plural = 'Retours'