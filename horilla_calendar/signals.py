"""
Signal handlers for the horilla_calendar app.

This module defines Django signal receivers related to calendar functionality,
for example creating default shortcut keys for newly created users.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from horilla.auth.models import User
from horilla_keys.models import ShortcutKey


# Define your  signals here
@receiver(post_save, sender=User)
def create_calendar_shortcuts(sender, instance, created, **kwargs):
    """
    Add default calendar shortcut keys for newly created users.

    This signal handler runs after a User is saved and ensures that a predefined
    set of `ShortcutKey` entries exist for the user (creates them if missing).
    """
    predefined = [
        {"page": "/horilla_calendar/calendar-view/", "key": "I", "command": "alt"},
    ]

    for item in predefined:
        if not ShortcutKey.objects.filter(user=instance, page=item["page"]).exists():
            ShortcutKey.objects.create(
                user=instance,
                page=item["page"],
                key=item["key"],
                command=item["command"],
                company=instance.company,
            )
