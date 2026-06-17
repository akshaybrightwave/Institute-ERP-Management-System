import os
import sys
import django

# Bootstrap Django
sys.path.append(r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append('testserver')

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.template import loader
from django.contrib.auth.models import AnonymousUser
from apps.batches.models import Batch
from apps.attendance.views import attendance_create

User = get_user_model()

def test_navigation():
    print("==================================================")
    print("RUNNING NAVIGATION & REDIRECT FIXES CHECKS")
    print("==================================================")

    # 1. Verify @login_required on attendance_create
    factory = RequestFactory()
    request = factory.get('/attendance/create/')
    request.user = AnonymousUser()
    
    response = attendance_create(request)
    if response.status_code == 302 and 'login' in response.url:
        print("[OK] attendance_create is properly protected by login_required redirecting to login page.")
    else:
        print(f"[FAIL] attendance_create did not redirect anonymous user to login page! Status code: {response.status_code}")

    # 2. Test Attendance Reports Back Button in reports/attendance_report.html
    center_user = User(username="test_center", role="center")
    admin_user = User(username="test_admin", role="admin")

    template = loader.get_template('reports/attendance_report.html')
    
    # Render for center user
    request_center = factory.get('/reports/attendance/')
    request_center.user = center_user
    context_center = {
        'request': request_center,
        'records': [],
        'batches': [],
        'students': [],
        'courses': [],
    }
    rendered_center = template.render(context_center, request_center)
    if 'href="/centers/dashboard/"' in rendered_center:
        print("[OK] Attendance Report back button correctly points to Center Dashboard for Center user.")
    else:
        print("[FAIL] Attendance Report back button does not point to Center Dashboard for Center user.")

    if 'href="/reports/"' not in rendered_center:
        print("[OK] Attendance Report back button does not show general reports dashboard link for Center user.")
    else:
        print("[FAIL] Attendance Report back button still shows general reports dashboard link for Center user.")

    # Render for admin user
    request_admin = factory.get('/reports/attendance/')
    request_admin.user = admin_user
    context_admin = {
        'request': request_admin,
        'records': [],
        'batches': [],
        'students': [],
        'courses': [],
    }
    rendered_admin = template.render(context_admin, request_admin)
    if 'href="/reports/"' in rendered_admin:
        print("[OK] Attendance Report back button correctly points to Reports Dashboard for Admin user.")
    else:
        print("[FAIL] Attendance Report back button does not point to Reports Dashboard for Admin user.")

    # 3. Test Mark Attendance Back and Cancel Buttons in attendance/mark_attendance.html
    mock_batch = Batch.objects.first()
    if not mock_batch:
        print("Skipping mark_attendance template test: No batch found in DB.")
        return

    template_mark = loader.get_template('attendance/mark_attendance.html')

    # Render for center user
    request_center_mark = factory.get(f'/attendance/mark/{mock_batch.id}/')
    request_center_mark.user = center_user
    context_center_mark = {
        'request': request_center_mark,
        'batch': mock_batch,
        'selected_date': '2026-06-17',
        'student_list': [{'student': {'id': 1, 'full_name': 'Test Student', 'email': 'test@test.com'}, 'status': 'present'}],
        'is_admin': False,
    }
    rendered_center_mark = template_mark.render(context_center_mark, request_center_mark)
    
    # Back button check: should point to batch_detail
    expected_back_url = f'/batches/{mock_batch.id}/'
    if f'href="{expected_back_url}"' in rendered_center_mark:
        print("[OK] Mark Attendance Back button correctly points to batch_detail for Center user.")
    else:
        print(f"[FAIL] Mark Attendance Back button does not point to {expected_back_url} for Center user.")

    # Cancel button check: should point to attendance_list
    if 'href="/attendance/"' in rendered_center_mark:
        print("[OK] Mark Attendance Cancel button is present and correctly points to Attendance List.")
    else:
        print("[FAIL] Mark Attendance Cancel button is missing or incorrect.")

    # Render for teacher user
    teacher_user = User(username="test_teacher", role="teacher")
    request_teacher_mark = factory.get(f'/attendance/mark/{mock_batch.id}/')
    request_teacher_mark.user = teacher_user
    context_teacher_mark = {
        'request': request_teacher_mark,
        'batch': mock_batch,
        'selected_date': '2026-06-17',
        'student_list': [{'student': {'id': 1, 'full_name': 'Test Student', 'email': 'test@test.com'}, 'status': 'present'}],
        'is_admin': False,
    }
    rendered_teacher_mark = template_mark.render(context_teacher_mark, request_teacher_mark)
    expected_teacher_back_url = f'/teacher/batches/{mock_batch.id}/'
    if f'href="{expected_teacher_back_url}"' in rendered_teacher_mark:
        print("[OK] Mark Attendance Back button correctly points to teacher_batch_detail for Teacher user.")
    else:
        print(f"[FAIL] Mark Attendance Back button does not point to {expected_teacher_back_url} for Teacher user.")

    print("==================================================")

if __name__ == '__main__':
    test_navigation()
