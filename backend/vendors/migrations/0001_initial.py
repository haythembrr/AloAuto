# Generated by Django 5.2.1 on 2025-05-20 21:44

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Vendor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company_name', models.CharField(max_length=255)),
                ('tax_number', models.CharField(max_length=50, unique=True)),
                ('status', models.CharField(choices=[('pending', 'En attente'), ('active', 'Validé'), ('suspended', 'Suspendu')], default='pending', max_length=20)),
                ('bank_info', models.JSONField(blank=True, null=True)),
                ('logo', models.ImageField(blank=True, upload_to='vendors/logos/')),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Vendeur',
                'verbose_name_plural': 'Vendeurs',
            },
        ),
    ]
