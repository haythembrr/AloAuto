import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
# Use the same settings module as manage.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aloauto.settings')

app = Celery('aloauto') # Replace 'aloauto' with your project's name if different

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True) # ignore_result=True for debug task usually
def debug_task(self):
    print(f'Request: {self.request!r}')
