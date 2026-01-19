"""
Horilla generics app configuration.

This module defines the AppConfig for the horilla_generics application and performs
application startup tasks such as URL registration and signal imports.
"""

from django.apps import AppConfig


class HorillaGenericsConfig(AppConfig):
    """App configuration for horilla_generics application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "horilla_generics"

    def ready(self):
        try:
            # Auto-register this app's URLs and add to installed apps
            from django.urls import include, path

            from horilla.urls import urlpatterns

            urlpatterns.append(
                path(
                    "generics/",
                    include("horilla_generics.urls", namespace="horilla_generics"),
                ),
            )
            __import__("horilla_generics.signals")
        except Exception as e:
            import logging

            logging.warning("HorillaGenericsConfig.ready failed: %s", e)
            pass

        super().ready()
