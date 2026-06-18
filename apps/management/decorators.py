from django.http import HttpResponseForbidden
from functools import wraps

def telecaller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('admin', 'telecaller'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Telecaller Portal access only.")
    return wrapper
