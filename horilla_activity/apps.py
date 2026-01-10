"""App configuration for the activity module."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class HorillaActivityConfig(AppConfig):
    """
    Configuration class for the Activity app in Horilla.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_activity"
    verbose_name = _("Activity")

    def get_api_paths(self):
        """
        Return API path configurations for this app.

        Returns:
            list: List of dictionaries containing path configuration
        """
        return [
            {
                "pattern": "/activity/",
                "view_or_include": "horilla_activity.api.urls",
                "name": "horilla_activity_api",
                "namespace": "horilla_activity",
            }
        ]

    def ready(self):
        try:
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path("activity/", include("horilla_activity.urls")),
            )

            __import__("horilla_activity.registration")
            __import__("horilla_activity.methods")
            __import__("horilla_activity.menu")  # noqa: F401
            __import__("horilla_activity.signals")  # noqa:F401
        except Exception as e:
            import logging

            logging.warning("ActivityConfig.ready failed: %s", e)

        super().ready()
