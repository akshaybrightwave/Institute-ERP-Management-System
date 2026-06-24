from datetime import datetime, time
from decimal import Decimal

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db import IntegrityError
from django.dispatch import receiver
from django.utils import timezone

from .models import ExternalAttendanceLog, ExternalEmployee


def client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '') if request else ''
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') if request else ''


def employee_for_user(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
        
    try:
        profile = getattr(user, 'external_employee_profile', None)
        if profile:
            return profile
    except Exception:
        pass

    employee = None
    user_email = getattr(user, 'email', '').strip()
    user_username = getattr(user, 'username', '').strip()
    
    if user_email:
        employee = ExternalEmployee.objects.filter(email__iexact=user_email).first()
    if not employee and user_username:
        employee = ExternalEmployee.objects.filter(employee_id__iexact=user_username).first()

    if employee and not getattr(employee, 'user_id', None):
        employee.user = user
        try:
            employee.save(update_fields=['user', 'updated_at'])
        except Exception:
            try:
                employee.save()
            except Exception:
                pass
    return employee


def attendance_values(check_in, check_out):
    working_hours = None
    if check_in and check_out:
        start = datetime.combine(timezone.localdate(), check_in)
        end = datetime.combine(timezone.localdate(), check_out)
        if end >= start:
            minutes = int((end - start).total_seconds() // 60)
            working_hours = round(Decimal(minutes) / Decimal(60), 2)

    late_minutes = 0
    office_start = time(9, 0)
    late_cutoff = time(9, 15)
    if check_in and check_in > late_cutoff:
        check_in_dt = datetime.combine(timezone.localdate(), check_in)
        start_dt = datetime.combine(timezone.localdate(), office_start)
        late_minutes = int((check_in_dt - start_dt).total_seconds() // 60)
    return working_hours, late_minutes


@receiver(user_logged_in)
def mark_external_check_in(sender, request, user, **kwargs):
    employee = employee_for_user(user)
    if not employee:
        return

    now = timezone.localtime()
    log, _ = ExternalAttendanceLog.objects.get_or_create(
        employee=employee,
        date=now.date(),
        defaults={
            'status': 'present',
            'check_in': now.time(),
            'location_ip': client_ip(request),
            'last_activity': now,
            'marked_by': user,
            'notes': 'Auto marked from login.',
        },
    )
    changed_fields = ['status', 'location_ip', 'last_activity', 'marked_by', 'updated_at']
    if not log.check_in:
        log.check_in = now.time()
        changed_fields.append('check_in')
    log.status = 'present'
    log.location_ip = client_ip(request)
    log.last_activity = now
    log.marked_by = user
    if 'Auto marked' not in (log.notes or ''):
        log.notes = (log.notes + '\n' if log.notes else '') + 'Auto marked from login.'
        changed_fields.append('notes')
    working_hours, late_minutes = attendance_values(log.check_in, log.check_out)
    log.working_hours = working_hours
    log.late_minutes = late_minutes
    changed_fields.extend(['working_hours', 'late_minutes'])
    log.save(update_fields=list(dict.fromkeys(changed_fields)))


@receiver(user_logged_out)
def mark_external_check_out(sender, request, user, **kwargs):
    employee = employee_for_user(user)
    if not employee:
        return

    now = timezone.localtime()
    log, _ = ExternalAttendanceLog.objects.get_or_create(
        employee=employee,
        date=now.date(),
        defaults={
            'status': 'present',
            'location_ip': client_ip(request),
            'last_activity': now,
            'marked_by': user,
            'notes': 'Auto marked from logout.',
        },
    )
    log.status = 'present'
    log.check_out = now.time()
    log.location_ip = client_ip(request)
    log.last_activity = now
    log.marked_by = user
    if 'logout' not in (log.notes or '').lower():
        log.notes = (log.notes + '\n' if log.notes else '') + 'Auto marked from logout.'
    log.working_hours, log.late_minutes = attendance_values(log.check_in, log.check_out)
    log.save(update_fields=[
        'status',
        'check_out',
        'location_ip',
        'last_activity',
        'marked_by',
        'notes',
        'working_hours',
        'late_minutes',
        'updated_at',
    ])
