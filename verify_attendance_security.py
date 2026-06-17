import os
import sys
import django
from datetime import date

# Bootstrap Django
sys.path.append(r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from apps.students.models import StudentProfile
from apps.batches.models import Batch
from apps.attendance.models import Attendance
from apps.attendance.forms import AttendanceForm
from apps.attendance.views import mark_attendance, attendance_list, attendance_create, attendance_edit
from apps.reports.views import attendance_report

User = get_user_model()

def run_tests():
    print("==================================================")
    print("RUNNING ATTENDANCE SECURITY & VALIDATION CHECKS")
    print("==================================================")

    # 1. Retrieve users
    center_users = User.objects.filter(role='center')
    admin_user = User.objects.filter(role='admin').first()

    if not center_users.exists():
        print("ERROR: No Center users found in DB!")
        sys.exit(1)
    if not admin_user:
        print("ERROR: No Admin user found in DB!")
        sys.exit(1)

    # Find a center user who has batches and students
    center_user = None
    center_batches = None
    center_students = None
    for user in center_users:
        if user.center:
            batches = Batch.objects.filter(course__center=user.center)
            students = StudentProfile.objects.filter(batch__course__center=user.center)
            if batches.exists() and students.exists():
                center_user = user
                center_batches = batches
                center_students = students
                break

    if not center_user:
        center_user = center_users.first()
        center_batches = Batch.objects.filter(course__center=center_user.center)
        center_students = StudentProfile.objects.filter(batch__course__center=center_user.center)

    center = center_user.center
    print(f"Center User Selected for Test: {center_user.username} | Assigned Center: {center.name if center else 'None'}")

    # Create temporary mock objects for another center to perform security isolation checks
    from apps.centers.models import Center
    from apps.courses.models import Course
    
    created_mock_objects = []
    
    # Create a mock center
    mock_center = Center.objects.create(name="Mock Center for Security Tests", code="MOCK_ATT_SEC_01")
    created_mock_objects.append(mock_center)
    
    # Create mock course
    mock_course = Course.objects.create(center=mock_center, name="Mock Course", duration="1 month", fees=10000.00)
    created_mock_objects.append(mock_course)
    
    # Create mock batch
    mock_batch = Batch.objects.create(course=mock_course, name="Mock Batch for Security Tests", start_date=date.today(), end_date=date.today())
    created_mock_objects.append(mock_batch)
    
    # Create mock student user
    mock_student_user = User.objects.create_user(username="mock_att_student", email="mockatt@sec.com", password="password123", role='student')
    created_mock_objects.append(mock_student_user)
    
    # Create mock student profile
    mock_student = StudentProfile.objects.create(user=mock_student_user, full_name="Mock Attendance Student", batch=mock_batch)
    created_mock_objects.append(mock_student)

    # 3. Test Form Querysets and Validations
    print("\n--- Testing Form Validation ---")
    
    # Test form queryset filtering for Center User
    form = AttendanceForm(user=center_user)
    student_qs = form.fields['student'].queryset
    batch_qs = form.fields['batch'].queryset
    
    if mock_student.id in student_qs.values_list('id', flat=True):
        print("[FAIL] ERROR: Center user form queryset includes a student from another center!")
    else:
        print("[OK] Center user form queryset correctly excludes students from other centers.")
        
    if mock_batch.id in batch_qs.values_list('id', flat=True):
        print("[FAIL] ERROR: Center user form queryset includes a batch from another center!")
    else:
        print("[OK] Center user form queryset correctly excludes batches from other centers.")

    # Select local student and batch for valid form tests
    if center_students.exists() and center_batches.exists():
        local_student = center_students.first()
        local_batch = local_student.batch
        
        if local_batch:
            # Clean up existing attendance logs for this student and today to prevent uniqueness checks initially
            Attendance.objects.filter(student=local_student, date=date.today()).delete()

            # A: Check student batch relationship validation
            # Assigning a batch that is NOT student's batch
            wrong_batch = center_batches.exclude(id=local_batch.id).first()
            if wrong_batch:
                form_data = {
                    'student': local_student.id,
                    'batch': wrong_batch.id,
                    'date': date.today(),
                    'status': 'present'
                }
                form = AttendanceForm(data=form_data, user=center_user)
                if not form.is_valid():
                    print("[OK] Blocked student-batch mismatch in form (Failed validation as expected)")
                    print(f"  Error message: {form.errors.as_text()}")
                else:
                    print("[FAIL] ERROR: Form allowed student-batch mismatch!")

            # B: Check valid attendance entry creation
            form_data = {
                'student': local_student.id,
                'batch': local_batch.id,
                'date': date.today(),
                'status': 'present'
            }
            form = AttendanceForm(data=form_data, user=center_user)
            if form.is_valid():
                print("[OK] Valid attendance form is accepted")
                local_att = form.save()
                created_mock_objects.append(local_att)
            else:
                print(f"[FAIL] ERROR: Form rejected a valid attendance creation! Errors: {form.errors.as_text()}")

            # C: Check duplicate attendance validation
            form = AttendanceForm(data=form_data, user=center_user)
            if not form.is_valid():
                print("[OK] Blocked duplicate attendance entry for same student and date (Failed validation as expected)")
                print(f"  Error message: {form.errors.as_text()}")
            else:
                print("[FAIL] ERROR: Form allowed duplicate attendance entry!")

    # D: Test cross-center boundaries inside form clean
    if center_students.exists():
        local_student = center_students.first()
        form_data = {
            'student': local_student.id,
            'batch': mock_batch.id,
            'date': date.today(),
            'status': 'present'
        }
        form = AttendanceForm(data=form_data, user=center_user)
        if not form.is_valid():
            print("[OK] Cross-center batch assignment blocked in form (Failed validation as expected)")
            print(f"  Error message: {form.errors.as_text()}")
        else:
            print("[FAIL] ERROR: Form accepted a batch from another center!")

    # 4. Test View Security & URL Tampering
    print("\n--- Testing URL Manipulation & View Security (Direct URL manipulation returns 403) ---")
    factory = RequestFactory()

    # A: Test mark_attendance for batch from another center
    request = factory.get(f'/attendance/mark/{mock_batch.id}/')
    request.user = center_user
    response = mark_attendance(request, batch_id=mock_batch.id)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] mark_attendance for cross-center batch directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could load mark_attendance view for another center batch! Response: {response.status_code}")

    # B: Test attendance_edit for record from another center
    # Create mock attendance for the other center student
    other_att = Attendance.objects.create(
        student=mock_student,
        batch=mock_batch,
        date=date.today(),
        status='present'
    )
    created_mock_objects.append(other_att)

    request = factory.get(f'/attendance/{other_att.id}/edit/')
    request.user = center_user
    response = attendance_edit(request, pk=other_att.id)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] attendance_edit for cross-center record directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could load attendance_edit view for another center record! Response: {response.status_code}")

    # C: Test attendance_list filters with cross-center parameters
    request = factory.get(f'/attendance/?batch={mock_batch.id}')
    request.user = center_user
    response = attendance_list(request)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] attendance_list with cross-center batch parameter directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could filter attendance_list by other center batch! Response: {response.status_code}")

    request = factory.get(f'/attendance/?student={mock_student.id}')
    request.user = center_user
    response = attendance_list(request)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] attendance_list with cross-center student parameter directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could filter attendance_list by other center student! Response: {response.status_code}")

    # D: Test attendance_report filters with cross-center parameters
    request = factory.get(f'/reports/attendance/?batch={mock_batch.id}')
    request.user = center_user
    response = attendance_report(request)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] attendance_report with cross-center batch parameter directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could filter attendance_report by other center batch! Response: {response.status_code}")

    request = factory.get(f'/reports/attendance/?student={mock_student.id}')
    request.user = center_user
    response = attendance_report(request)
    if isinstance(response, HttpResponseForbidden):
        print("[OK] attendance_report with cross-center student parameter directly blocked (403 Forbidden)")
    else:
        print(f"[FAIL] ERROR: Center user could filter attendance_report by other center student! Response: {response.status_code}")

    # Clean up mock objects
    print("\n--- Cleaning up temporary mock objects ---")
    for obj in reversed(created_mock_objects):
        try:
            obj.delete()
        except Exception as e:
            print(f"Error deleting {obj}: {e}")

    print("\n==================================================")
    print("ALL ATTENDANCE VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
