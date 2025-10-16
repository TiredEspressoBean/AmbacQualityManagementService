from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Tracker'
    verbose_name = 'Inventory Management'

    def ready(self):
        import Tracker.signals  # Import signals when app starts
