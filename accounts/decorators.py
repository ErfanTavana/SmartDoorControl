from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .views import role_redirect


def role_required(role):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user_role = getattr(request.user, "role", None)
            if user_role != role:
                return redirect(role_redirect(request.user))
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


def head_required(view_func):
    return role_required("HEAD")(view_func)


def member_required(view_func):
    return role_required("MEMBER")(view_func)
