"""
Helper methods for Activity models
"""

from django.contrib.contenttypes.models import ContentType
from django.db import models

from horilla.registry.feature import FEATURE_REGISTRY

# Store original ContentType.__str__ to restore if needed
_original_contenttype_str = ContentType.__str__


def _is_activity_related_contenttype(content_type):
    """Check if ContentType is registered for activity_related feature"""
    activity_related_models = FEATURE_REGISTRY.get("activity_related_models", [])
    if not activity_related_models:
        return False
    for model in activity_related_models:
        if (
            content_type.app_label == model._meta.app_label
            and content_type.model == model._meta.model_name.lower()
        ):
            return True
    return False


def _contenttype_str_override(self):
    """Override ContentType.__str__ to show only model name for activity_related models"""
    # Check if this ContentType is activity_related
    if _is_activity_related_contenttype(self):
        model_cls = self.model_class()
        if model_cls:
            return model_cls._meta.verbose_name.title()
        # Fallback: format model name nicely
        return self.model.replace("_", " ").title()
    # For non-activity_related models, use original __str__
    return _original_contenttype_str(self)


# Patch ContentType.__str__ at class level
ContentType.__str__ = _contenttype_str_override


def limit_content_types():
    """
    Limit ContentType choices to only models that have
    'activity_related' feature enabled.

    This ensures Activity can only be linked to models registered
    for activity_related feature.
    """
    activity_related_models = FEATURE_REGISTRY.get("activity_related_models", [])

    if not activity_related_models:
        return models.Q(pk__in=[])

    # Build Q object matching both app_label and model
    q_objects = models.Q()
    for model in activity_related_models:
        q_objects |= models.Q(
            app_label=model._meta.app_label, model=model._meta.model_name.lower()
        )

    return q_objects


def get_content_type_display_name(content_type):
    """
    Get display name for ContentType showing only model name (not app_label.model).
    Used for Select2 and form displays.
    """
    model_cls = content_type.model_class()
    if model_cls:
        return model_cls._meta.verbose_name.title()
    # Fallback: format model name nicely
    return content_type.model.replace("_", " ").title()


def get_activity_content_types_queryset():
    """
    Get ContentType queryset for models registered for activity_related feature.
    This can be used directly in forms.

    Note: For Select2 AJAX, we need to patch __str__ on ContentType objects
    since Select2 uses str(obj). This is done in the form when the queryset is used.
    """
    activity_related_models = FEATURE_REGISTRY.get("activity_related_models", [])

    if not activity_related_models:
        return ContentType.objects.none()

    # Build Q object matching both app_label and model
    q_objects = models.Q()
    for model in activity_related_models:
        q_objects |= models.Q(
            app_label=model._meta.app_label, model=model._meta.model_name.lower()
        )

    return ContentType.objects.filter(q_objects)
