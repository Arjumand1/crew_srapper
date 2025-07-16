from django.apps import AppConfig

class CrewSheetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crew_sheets'
    
    def ready(self):
        # Import signals to register them
        import crew_sheets.signals
