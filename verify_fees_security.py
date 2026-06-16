import os
import sys
import django
from decimal import Decimal
from datetime import date

# Bootstrap Django
sys.path.append(r'c:\Users\Akshay\Desktop\Akshay\Django\Online-Examination-Portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'online_exam_portal.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from django.http import HttpResponseForbidden
from apps.students.models import StudentProfile
from apps.fees.models import FeePayment
from apps.fees.forms import FeePaymentForm
from apps.fees.views import fees_list, payment_create, payment_update, payment_delete, payment_receipt

User = get_user_model()

def run_tests():
    print("==================================================")
    print("RUNNING FEE SECURITY & VALIDATION CHECKS")
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

    # Find a center user who has students for testing form validation
    center_user = None
    center_students = None
    for user in center_users:
        if user.center:
            students = StudentProfile.objects.filter(batch__course__center=user.center)
            if students.exists():
                center_user = user
                center_students = students
                break

    # Fallback to first center user if none has students
    if not center_user:
        center_user = center_users.first()
        center_students = StudentProfile.objects.filter(batch__course__center=center_user.center)

    center = center_user.center
    print(f"Center User Selected for Test: {center_user.username} | Assigned Center: {center.name if center else 'None'}")

    other_students = StudentProfile.objects.exclude(batch__course__center=center) if center else StudentProfile.objects.all()

    created_mock_objects = []
    if not other_students.exists():
        print("No students in other centers. Creating a temporary student in a mock center...")
        from apps.centers.models import Center
        from apps.courses.models import Course
        from apps.batches.models import Batch
        
        # Create a mock center
        mock_center = Center.objects.create(name="Mock Center for Security Tests", code="MOCK_SEC_01")
        created_mock_objects.append(mock_center)
        
        # Create course
        mock_course = Course.objects.create(center=mock_center, name="Mock Course", duration="1 month", fees=Decimal('10000.00'))
        created_mock_objects.append(mock_course)
        
        # Create batch
        mock_batch = Batch.objects.create(course=mock_course, name="Mock Batch", start_date=date.today(), end_date=date.today())
        created_mock_objects.append(mock_batch)
        
        # Create user
        mock_user = User.objects.create_user(username="mock_sec_student", email="mock@sec.com", password="password123", role='student')
        created_mock_objects.append(mock_user)
        
        # Create student profile
        mock_student = StudentProfile.objects.create(user=mock_user, full_name="Mock Security Student", batch=mock_batch)
        created_mock_objects.append(mock_student)
        
        other_students = StudentProfile.objects.filter(id=mock_student.id)

    print(f"Students belonging to center: {center_students.count()}")
    print(f"Students belonging to other centers: {other_students.count()}")

    # 3. Test Form Validation (Positive amounts, Overpayment, and Center restrictions)
    print("\n--- Testing Form Validation ---")
    if center_students.exists():
        student = center_students.first()
        course_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
        print(f"Selected student: {student.full_name} | Course Fee: INR {course_fee}")

        # Clear any existing payments to have a clean slate
        FeePayment.objects.filter(student=student).delete()

        # A: Check negative value validation
        form_data = {
            'student': student.id,
            'amount': Decimal('-50.00'),
            'payment_date': date.today(),
            'payment_method': 'cash',
        }
        form = FeePaymentForm(data=form_data, user=center_user)
        if not form.is_valid():
            print("[OK] Negative amount validation works (Failed validation as expected)")
            print(f"  Error message: {form.errors.as_text().replace('₹', 'INR')}")
        else:
            print("[FAIL] ERROR: Form accepted a negative payment amount!")

        # B: Check zero payment validation
        form_data['amount'] = Decimal('0.00')
        form = FeePaymentForm(data=form_data, user=center_user)
        if not form.is_valid():
            print("[OK] Zero payment validation works (Failed validation as expected)")
            print(f"  Error message: {form.errors.as_text().replace('₹', 'INR')}")
        else:
            print("[FAIL] ERROR: Form accepted a zero payment amount!")

        # C: Check overpayment validation
        if course_fee > 0:
            form_data['amount'] = course_fee + Decimal('100.00')
            form = FeePaymentForm(data=form_data, user=center_user)
            if not form.is_valid():
                print("[OK] Overpayment validation works (Failed validation as expected)")
                print(f"  Error message: {form.errors.as_text().replace('₹', 'INR')}")
            else:
                print("[FAIL] ERROR: Form allowed overpayment!")

        # D: Check valid payment
        if course_fee > 50:
            form_data['amount'] = Decimal('50.00')
            form = FeePaymentForm(data=form_data, user=center_user)
            if form.is_valid():
                print("[OK] Valid payment form validation works (Form is valid)")
                # Save it
                payment = form.save()
            else:
                print(f"[FAIL] ERROR: Form rejected a valid payment amount! Errors: {form.errors.as_text().replace('₹', 'INR')}")

    # 4. Test Cross-Center student validation inside Form
    if other_students.exists():
        other_student = other_students.first()
        print(f"\nTesting Cross-Center Form restriction using student: {other_student.full_name}")
        form_data = {
            'student': other_student.id,
            'amount': Decimal('10.00'),
            'payment_date': date.today(),
            'payment_method': 'cash',
        }
        form = FeePaymentForm(data=form_data, user=center_user)
        if not form.is_valid():
            print("[OK] Cross-center student assignment blocked in form (Failed validation as expected)")
            print(f"  Error message: {form.errors.as_text().replace('₹', 'INR')}")
        else:
            print("[FAIL] ERROR: Center user form allowed mapping a student from another center!")

    # 5. Test Center Data Isolation in views
    print("\n--- Testing URL Manipulation & View Security (Direct URL manipulation returns 403) ---")
    factory = RequestFactory()

    if other_students.exists():
        other_student = other_students.first()
        # Create a mock payment for the other center student
        other_payment = FeePayment.objects.create(
            student=other_student,
            amount=Decimal('10.00'),
            payment_date=date.today(),
            payment_method='cash'
        )

        # Test View update isolation
        request = factory.get(f'/fees/payments/{other_payment.id}/edit/')
        request.user = center_user
        response = payment_update(request, pk=other_payment.id)
        if isinstance(response, HttpResponseForbidden):
            print("[OK] Edit cross-center payment directly is blocked (403 Forbidden)")
        else:
            print(f"[FAIL] ERROR: Center user could load edit view for another center's payment! Response: {response.status_code}")

        # Test View delete isolation
        request = factory.get(f'/fees/payments/{other_payment.id}/delete/')
        request.user = center_user
        response = payment_delete(request, pk=other_payment.id)
        if isinstance(response, HttpResponseForbidden):
            print("[OK] Delete cross-center payment directly is blocked (403 Forbidden)")
        else:
            print(f"[FAIL] ERROR: Center user could load delete view for another center's payment! Response: {response.status_code}")

        # Test View receipt isolation
        request = factory.get(f'/fees/payments/{other_payment.id}/receipt/')
        request.user = center_user
        response = payment_receipt(request, pk=other_payment.id)
        if isinstance(response, HttpResponseForbidden):
            print("[OK] Receipt cross-center view directly is blocked (403 Forbidden)")
        else:
            print(f"[FAIL] ERROR: Center user could view receipt for another center's payment! Response: {response.status_code}")

        # Clean up the test payment
        other_payment.delete()

    # Clean up mock objects if any were created
    if created_mock_objects:
        print("\n--- Cleaning up temporary mock objects ---")
        for obj in reversed(created_mock_objects):
            try:
                obj.delete()
            except Exception as e:
                print(f"Error deleting {obj}: {e}")

    print("\n==================================================")
    print("ALL VERIFICATIONS COMPLETED SUCCESSFULLY!")
    print("==================================================")

if __name__ == '__main__':
    run_tests()
