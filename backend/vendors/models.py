from django.db import models
from django.conf import settings

class Vendor(models.Model):
    STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('active', 'Validé'),
        ('suspended', 'Suspendu'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255)
    tax_number = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    bank_info = models.JSONField(blank=True, null=True)
    logo = models.ImageField(upload_to='vendors/logos/', blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Vendeur'
        verbose_name_plural = 'Vendeurs'