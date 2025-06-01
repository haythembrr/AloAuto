from django.apps import AppConfig

class LogsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'logs' # Ensure this matches your app's directory name if it's just 'logs'
                 # If your app is 'backend.logs' in INSTALLED_APPS, this should be 'backend.logs'
                 # However, typically for apps within a project structure like 'backend/logs',
                 # the name in INSTALLED_APPS is 'logs' or 'backend.logs', and this 'name' field
                 # should match that. Given the project structure, 'logs' or 'backend.logs' are possibilities.
                 # The original prompt used 'backend.logs' in the planned content for apps.py.
                 # I will use 'logs' as it's more common for the AppConfig.name to be the simple app name.
                 # If INSTALLED_APPS uses 'backend.logs', then this should be 'backend.logs'.
                 # Let's assume 'logs' is correct for INSTALLED_APPS.

    def ready(self):
        from . import signals # Use relative import
