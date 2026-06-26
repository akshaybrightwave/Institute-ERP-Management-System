def get_client_ip(request):
    if not request:
        return None
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_auth_activity(event_type, request=None, user=None, username='', details=''):
    try:
        from .models import AuthActivityLog

        AuthActivityLog.objects.create(
            user=user if getattr(user, 'is_authenticated', False) else None,
            username=(username or getattr(user, 'username', '') or '')[:150],
            event_type=event_type,
            ip_address=get_client_ip(request),
            user_agent=(request.META.get('HTTP_USER_AGENT', '')[:255] if request else ''),
            path=(request.path[:255] if request else ''),
            details=details,
        )
    except Exception:
        pass
