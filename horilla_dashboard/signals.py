"""
Signal handlers for the horilla_dashboard app.

This module contains Django signal receivers related to dashboard lifecycle
events (e.g., pre/post-save behavior).
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
