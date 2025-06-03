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
            self.stdout.write(self.style.WARNING("Starting forced data clearing..."))

            # Correct order considering foreign key dependencies
            MODELS_TO_CLEAR_ORDER = [
                # First level - No dependencies
                ('catalogue', 'ProductImage'),
                ('payments', 'Payment'),
                ('shipping', 'Shipment'),
                ('support', 'Ticket'),
                ('integrations', 'ERPSyncLog'),
                ('integrations', 'FileUploadLog'),
                
                # Second level - Depends on products/orders
                ('orders', 'OrderItem'),
                ('orders', 'CartItem'),
                
                # Third level - Main entities
                ('orders', 'Order'),
                ('orders', 'Cart'),
                ('orders', 'Wishlist'),
                ('catalogue', 'Product'),
                
                # Fourth level - Categories and vendors
                ('catalogue', 'Category'),
                ('vendors', 'Vendor'),
                
                # Fifth level - User related
                ('accounts', 'Address'),
                ('accounts', 'User'),  # Now included for complete reset
            ]

            connection = connections[DEFAULT_DB_ALIAS]
            with connection.cursor() as cursor:
                # Temporarily disable foreign key checks
                if connection.vendor == 'sqlite':
                    cursor.execute('PRAGMA foreign_keys = OFF;')
                elif connection.vendor == 'mysql':
                    cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')
                elif connection.vendor == 'postgresql':
                    cursor.execute('SET CONSTRAINTS ALL DEFERRED;')

                try:
                    for app_label, model_name in MODELS_TO_CLEAR_ORDER:
                        if self._model_exists(app_label, model_name):
                            from django.apps import apps
                            model = apps.get_model(app_label, model_name)
                            table_name = model._meta.db_table
                            self.stdout.write(f"Force clearing {app_label}.{model_name}...")
                            
                            try:
                                if connection.vendor == 'sqlite':
                                    cursor.execute(f"DELETE FROM {table_name};")
                                    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table_name}';")
                                elif connection.vendor in ('postgresql', 'mysql'):
                                    cursor.execute(f"TRUNCATE TABLE {table_name} CASCADE;")
                                
                                self.stdout.write(self.style.SUCCESS(f"Cleared {table_name}"))
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"Error clearing {table_name}: {e}"))
                        else:
                            self.stdout.write(
                                self.style.WARNING(f"Model {app_label}.{model_name} not found. Skipping.")
                            )

                finally:
                    # Re-enable foreign key checks
                    if connection.vendor == 'sqlite':
                        cursor.execute('PRAGMA foreign_keys = ON;')
                    elif connection.vendor == 'mysql':
                        cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')
                    elif connection.vendor == 'postgresql':
                        cursor.execute('SET CONSTRAINTS ALL IMMEDIATE;')

            self.stdout.write(self.style.SUCCESS("Forced data clearing completed successfully"))

    # ... rest of your populate code ...

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
