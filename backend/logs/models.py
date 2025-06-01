from django.db import models
from django.conf import settings

class Log(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='logs'
    )
    action = models.CharField(max_length=255)
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Journal'
        verbose_name_plural = 'Journaux'
        ordering = ['-created_at']