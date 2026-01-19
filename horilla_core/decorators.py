"""
Custom decorators used across Horilla for permission handling,
HTMX validation, and database initialization checks.
"""

from functools import wraps

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy


def permission_required_or_denied(
    perms, template_name="error/403.html", require_all=False, modal=False
):
    """
    Custom decorator for both FBVs and CBVs.
    - `perms`: single permission string or a list/tuple of permissions.
    - `require_all`: if True, user must have ALL permissions; if False, ANY one is enough.
    """

    if isinstance(perms, str):
        perms = [perms]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):

            request = args[0] if hasattr(args[0], "user") else args[1]
            user = request.user

            if not user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)
                # return render(request, "login.html")

            if require_all:
                has_permission = user.has_perms(perms)
            else:
                has_permission = user.has_any_perms(perms)

            if has_permission:
                return view_func(*args, **kwargs)
            return render(
                request, template_name, {"permissions": perms, "modal": modal}
            )

        return _wrapped_view

    return decorator


def permission_required(perms, require_all=False):
    """
    Custom decorator for both FBVs and CBVs.
    Returns 403 if user doesn't have required permission(s).
    """
    if isinstance(perms, str):
        perms = [perms]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            request = args[0] if hasattr(args[0], "user") else args[1]
            user = request.user

            if not user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)

            if require_all:
                has_permission = user.has_perms(perms)
            else:
                has_permission = user.has_any_perms(perms)

            if has_permission:
                return view_func(*args, **kwargs)
            return HttpResponse("")

        return _wrapped_view

    return decorator


def htmx_required(view_func=None, login=True):
    """
    Ensure the request is an HTMX request.
    Optionally enforce authentication before allowing access.
    """

    def decorator(func):
        @wraps(func)
        def _wrapped_view(request, *args, **kwargs):
            if login and not request.user.is_authenticated:
                login_url = f"{reverse_lazy('horilla_core:login')}?next={request.path}"
                return redirect(login_url)
            if not request.headers.get("HX-Request") == "true":
                return render(request, "error/405.html")
            return func(request, *args, **kwargs)

        return _wrapped_view

    # If called without arguments: @htmx_required
    if view_func is not None:
        return decorator(view_func)

    # If called with arguments: @htmx_required(login=False)
    return decorator


def db_initialization(model=None):
    """
    Decorator factory.
    @method_decorator(db_initialization(model=User), name="dispatch")
    """

    def actual_decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. Does the database still need initialization?
            needs_initialization = not model.objects.exists()

            # 2. Is the correct password stored in session?
            correct_password = settings.DB_INIT_PASSWORD
            password_valid = request.session.get("db_password") == correct_password

            # If DB is already initialized OR password is wrong → redirect away
            if not needs_initialization or not password_valid:
                next_url = request.GET.get("next", "/")
                return redirect(next_url)

            # Otherwise allow the original view to run
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return actual_decorator
