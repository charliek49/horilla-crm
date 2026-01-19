"""
Views for handling user password changes in Horilla.

Includes the password change page and an HTMX-enabled
form view for updating the user's password securely.
"""

# Third-party imports
from auditlog.models import LogEntry

# Django imports
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView, TemplateView

# Horilla first-party imports
from horilla.auth.models import User
from horilla_core.decorators import htmx_required
from horilla_core.forms import ChangePasswordForm


class ChangePasswordView(LoginRequiredMixin, TemplateView):
    """
    Display the password change page for the logged-in user.

    Shows the last password update time using audit log history.
    """

    template_name = "settings/change_password.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        model_name = User._meta.model_name

        last_change = (
            LogEntry.objects.filter(
                content_type__model=model_name,
                object_id=user.pk,
                changes__icontains='"password"',
            )
            .order_by("-timestamp")
            .first()
        )

        last_updated = last_change.timestamp
        user_date_format = (
            user.date_format
            if hasattr(user, "date_format") and user.date_format
            else "%Y-%m-%d"
        )

        context.update(
            {
                "user": user,
                "last_updated": last_updated.strftime(user_date_format),
            }
        )
        return context


@method_decorator(htmx_required, name="dispatch")
class ChangePasswordFormView(LoginRequiredMixin, FormView):
    """HTMX view to handle password change form"""

    template_name = "settings/change_password_form.html"
    form_class = ChangePasswordForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        user = self.request.user
        new_password = form.cleaned_data["new_password"]
        user.set_password(new_password)
        user.save()
        update_session_auth_hash(self.request, user)
        messages.success(
            self.request, _("Your password has been changed successfully.")
        )
        return HttpResponse("<script>closeModal();$('#reloadButton').click();</script>")

    def form_invalid(self, form):
        return render(
            self.request,
            self.template_name,
            {"form": form},
        )
