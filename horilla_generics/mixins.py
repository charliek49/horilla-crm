"""
Mixins for horilla_generics.

Provides reusable view mixins used by horilla_generics views.
"""

# Third-party imports (Django)
from django.contrib.auth.mixins import LoginRequiredMixin

# First-party / Horilla imports
from horilla_core.models import RecentlyViewed


class RecentlyViewedMixin(LoginRequiredMixin):
    """Mixin for automatically tracking recently viewed objects for authenticated users."""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if hasattr(self, "object") and self.object and request.user.is_authenticated:
            RecentlyViewed.objects.add_viewed_item(request.user, self.object)
        return response
