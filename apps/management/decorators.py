from django.http import HttpResponseForbidden
from functools import wraps

def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('superadmin', 'SUPER_ADMIN'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Super Admin access only.")
    return wrapper

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('admin', 'superadmin', 'SUPER_ADMIN'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Admin access only.")
    return wrapper

def telecaller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('telecaller', 'admin', 'superadmin', 'SUPER_ADMIN'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Telecaller/Admin access only.")
    return wrapper


def counselor_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('counselor', 'admin', 'superadmin', 'SUPER_ADMIN'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Counselor/Admin access only.")
    return wrapper

def telecaller_counselor_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('telecaller', 'counselor', 'admin', 'superadmin', 'SUPER_ADMIN'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Telecaller, Counselor, or Admin access only.")
    return wrapper
