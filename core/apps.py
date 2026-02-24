from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    def ready(self):
        # importing signals here to avoid circular imports
        # this is standard django practice
        import core.signals
