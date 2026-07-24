from django.http import HttpResponseForbidden
from django.contrib.auth import logout
from apps.accounts.auth_logging import log_auth_activity

class PortalAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        if not request.user.is_active or getattr(request.user, 'is_deleted', False):
            log_auth_activity(
                'SESSION_INVALID',
                request=request,
                user=request.user,
                username=request.user.username,
                details='Authenticated session belonged to an inactive or deleted account.',
            )
            logout(request)
            return HttpResponseForbidden("Access Denied: Your account session is no longer valid.")

        role = request.user.role
        path = request.path

        # Allow basic common paths like logout, login, static files, and media uploads
        if path.startswith('/logout') or path.startswith('/login') or path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Telecaller and Counselor role isolation: can ONLY access /management/*
        if role in ('telecaller', 'counselor'):
            if not path.startswith('/management/'):
                return HttpResponseForbidden("Access Denied: You only have access to the Management Portal.")

        # ERP roles (center, teacher, student) isolation: can NOT access /management/*
        elif role in ('center', 'teacher', 'student', 'investigator'):
            if path.startswith('/management/'):
                return HttpResponseForbidden("Access Denied: You do not have access to the Management Portal.")

        return self.get_response(request)
