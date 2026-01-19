"""Signal handlers for `horilla_reports` (connect model events to side-effects)."""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
