"""Signal handlers for horilla_activity app."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from horilla.auth.models import User
from horilla_keys.models import ShortcutKey


@receiver(post_save, sender=User)
def create_activity_shortcuts(sender, instance, created, **kwargs):
    """Create default activity shortcuts for new users."""
    predefined = [
        {"page": "/activity/activity-view/", "key": "Y", "command": "alt"},
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
