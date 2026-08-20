from django.apps import AppConfig


class PlacesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "places"

    def ready(self):
        from places import signals  # noqa: F401  신호 등록만 하면 되므로 import만 한다
