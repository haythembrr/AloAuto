# Generated by Django 5.0 on 2025-06-02 22:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('integrations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='erpsynclog',
            name='records_affected',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='erpsynclog',
            name='run_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='fileuploadlog',
            name='upload_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
