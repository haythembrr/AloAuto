# Generated by Django 5.0 on 2025-06-02 22:56

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_remove_address_is_default_address_is_default_billing_and_more'),
        ('orders', '0002_orderitem_price_at_purchase'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='billing_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='billing_orders', to='accounts.address'),
        ),
        migrations.AddField(
            model_name='order',
            name='billing_address_snapshot',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_address_snapshot',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_method',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='shipping_address',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='shipping_orders', to='accounts.address'),
        ),
    ]
