from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS, connections
from django.conf import settings # To get the list of installed apps

class Command(BaseCommand):
    help = 'Populates the database with all defined sample data by calling app-specific commands in order.'

    COMMANDS_IN_ORDER = [
        ('populate_accounts', 'accounts'),
        ('populate_vendors', 'vendors'),
        ('populate_catalogue', 'catalogue'),
        ('populate_orders', 'orders'),
        ('populate_payments', 'payments'),
        ('populate_shipping', 'shipping'),
        ('populate_returns', 'returns'),
        ('populate_support', 'support'),
        ('populate_integrations', 'integrations'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clears existing data from relevant tables before populating. Use with caution!',
        )

    def _model_exists(self, app_label, model_name):
        try:
            # Simple check, Django's get_model might be more robust if models are not yet loaded by apps.py
            # For management commands, apps should be ready.
            from django.apps import apps
            apps.get_model(app_label, model_name)
            return True
        except LookupError:
            return False

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING("Starting to clear existing data as per --clear option..."))

            # Important: Define models to clear in reverse order of dependency, or use app labels if models are complex.
            # This is a simplified clearing mechanism. For complex relationships with cascades,
            # direct model.objects.all().delete() in the correct order is more reliable.
            # For now, we will clear data from the models populated by each script.
            # This part needs to be implemented carefully based on actual model definitions and dependencies.

            # Example of clearing (models need to be imported):
            # from integrations.models import ERPSyncLog, FileUploadLog
            # from support.models import Ticket
            # from returns.models import ReturnRequest, ReturnItem
            # from shipping.models import Shipment
            # from payments.models import Payment
            # from orders.models import Order, OrderItem, Cart, CartItem, Wishlist
            # from catalogue.models import ProductImage, Product, Category
            # from vendors.models import Vendor
            # from accounts.models import Address, User # User last or handle carefully due to dependencies

            # Order of deletion should be reverse of creation and consider relations.
            # This is a best-effort generic clear. Specific clear commands might be better.
            MODELS_TO_CLEAR_ROUGH_ORDER = [
                ('integrations', 'FileUploadLog'), ('integrations', 'ERPSyncLog'),
                ('support', 'Ticket'),
                ('returns', 'ReturnItem'), ('returns', 'ReturnRequest'),
                ('shipping', 'Shipment'),
                ('payments', 'Payment'),
                ('orders', 'OrderItem'), ('orders', 'Order'),
                ('orders', 'CartItem'), ('orders', 'Cart'), ('orders', 'Wishlist'), # Wishlist products are M2M, usually safe
                ('catalogue', 'ProductImage'), ('catalogue', 'Product'), ('catalogue', 'Category'),
                ('vendors', 'Vendor'),
                ('accounts', 'Address'),
                # ('accounts', 'User'), # Clearing users is very destructive. Usually not done in populate scripts unless for a full reset.
                                      # If User is cleared, other tables are usually cascaded or raise errors.
                                      # For this script, we might skip User clearing to avoid issues with admin accounts etc.
                                      # Or only clear specific types of users.
            ]

            self.stdout.write(self.style.WARNING("Clearing Users is disabled by default in this script. Clear manually if needed."))

            connection = connections[DEFAULT_DB_ALIAS]
            with connection.cursor() as cursor:
                for app_label, model_name in reversed(MODELS_TO_CLEAR_ROUGH_ORDER):
                    if self._model_exists(app_label, model_name):
                        from django.apps import apps
                        model = apps.get_model(app_label, model_name)
                        table_name = model._meta.db_table
                        self.stdout.write(f"Clearing data from {app_label}.{model_name} (table: {table_name})...")
                        try:
                            # Using raw SQL for TRUNCATE or DELETE for speed and to bypass signals if desired.
                            # TRUNCATE is faster but might be locked or not available for referenced tables.
                            # DELETE FROM is safer.
                            cursor.execute(f"DELETE FROM {table_name};")
                            # For PostgreSQL, to reset sequences (optional, usually handled by Django):
                            # cursor.execute(f"ALTER SEQUENCE {table_name}_id_seq RESTART WITH 1;")
                            self.stdout.write(self.style.SUCCESS(f"Cleared {table_name}."))
                        except Exception as e:
                            self.stdout.write(self.style.ERROR(f"Error clearing {table_name}: {e}"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Model {app_label}.{model_name} not found for clearing. Skipping."))
            self.stdout.write(self.style.SUCCESS("Data clearing process finished (excluding Users by default)."))


        for command_name, app_name in self.COMMANDS_IN_ORDER:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\nRunning population command for {app_name}: {command_name}"))
            try:
                call_command(command_name)
                self.stdout.write(self.style.SUCCESS(f"Successfully populated data for {app_name}."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error running {command_name} for {app_name}: {e}"))
                self.stdout.write(self.style.WARNING("Stopping further population due to error."))
                # Optionally, re-raise the exception if you want the whole command to fail loudly
                # raise e
                break # Stop on error

        self.stdout.write(self.style.SUCCESS('\nAll data population commands executed.'))
