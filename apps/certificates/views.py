from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from decimal import Decimal

from apps.students.models import StudentProfile
from apps.teachers.models import TeacherProfile
from apps.attendance.models import Attendance
from apps.fees.models import FeePayment
from .models import Certificate
from .forms import CertificateForm


def get_student_eligibility(student):
    if not student.batch:
        return {
            'eligible': False,
            'reason': "Student has no assigned batch.",
            'attendance_pct': 0.0,
            'fee_status': 'PENDING',
            'pending_amount': Decimal('0.00'),
            'paid_amount': Decimal('0.00'),
            'course_fee': Decimal('0.00')
        }

    # Attendance calculations
    attendances = Attendance.objects.filter(student=student)
    total_att = attendances.count()
    if total_att > 0:
        present_count = attendances.filter(status='present').count()
        attendance_pct = round((present_count / total_att) * 100, 1)
    else:
        attendance_pct = 0.0

    attendance_eligible = attendance_pct >= 75.0

    # Fee calculations
    course_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
    paid_amount = FeePayment.objects.filter(student=student).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    course_fee = Decimal(str(course_fee))
    paid_amount = Decimal(str(paid_amount))
    pending_amount = course_fee - paid_amount

    if paid_amount == 0:
        fee_status = 'PENDING'
    elif pending_amount <= 0:
        fee_status = 'PAID'
    else:
        fee_status = 'PARTIAL'

    fee_eligible = pending_amount <= 0

    eligible = attendance_eligible and fee_eligible

    reasons = []
    if not attendance_eligible:
        reasons.append(f"Attendance is {attendance_pct}% (minimum 75% required).")
    if not fee_eligible:
        reasons.append(f"Fees pending: ₹{pending_amount} (must be PAID).")

    reason = " ".join(reasons) if reasons else "Eligible"

    return {
        'eligible': eligible,
        'reason': reason,
        'attendance_pct': attendance_pct,
        'fee_status': fee_status,
        'pending_amount': pending_amount,
        'paid_amount': paid_amount,
        'course_fee': course_fee
    }


@login_required
def certificate_list(request):
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    
    if not (is_admin or is_teacher):
        return HttpResponseForbidden("Access Denied: Admins or Teachers only.")
        
    certificates = Certificate.objects.all().select_related('student', 'batch', 'course')
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        certificates = certificates.filter(batch__teacher=teacher_profile)
        
    query = request.GET.get('q', '').strip()
    if query:
        certificates = certificates.filter(
            Q(certificate_number__icontains=query) |
            Q(student__full_name__icontains=query) |
            Q(batch__name__icontains=query) |
            Q(course__name__icontains=query)
        )
        
    certificates = certificates.order_by('-issue_date', '-id')
    
    paginator = Paginator(certificates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'certificates/certificate_list.html', {
        'page_obj': page_obj,
        'query': query,
        'is_admin': is_admin
    })


@login_required
def certificate_create(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")

    selected_student_id = request.GET.get('student')
    eligibility_info = None
    student_obj = None

    if selected_student_id:
        student_obj = get_object_or_404(StudentProfile, id=selected_student_id)
        eligibility_info = get_student_eligibility(student_obj)

    if request.method == 'POST':
        form = CertificateForm(request.POST)
        student_id = request.POST.get('student')
        if student_id:
            student_obj = get_object_or_404(StudentProfile, id=student_id)
            eligibility_info = get_student_eligibility(student_obj)
            
            if not eligibility_info['eligible']:
                form.add_error('student', f"This student is not eligible: {eligibility_info['reason']}")
            else:
                if form.is_valid():
                    cert = form.save(commit=False)
                    cert.batch = student_obj.batch
                    cert.course = student_obj.batch.course
                    cert.save()
                    messages.success(request, f"Certificate {cert.certificate_number} issued successfully.")
                    return redirect('certificate_list')
    else:
        form = CertificateForm(initial={'student': selected_student_id})

    return render(request, 'certificates/certificate_form.html', {
        'form': form,
        'eligibility_info': eligibility_info,
        'student_obj': student_obj
    })


@login_required
def certificate_detail(request, pk):
    certificate = get_object_or_404(Certificate.objects.select_related('student', 'batch', 'course'), pk=pk)
    
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    is_student = request.user.role == 'student'
    
    if is_student:
        if certificate.student.user != request.user:
            return HttpResponseForbidden("Access Denied: You can only view your own certificates.")
    elif is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        if certificate.batch.teacher != teacher_profile:
            return HttpResponseForbidden("Access Denied: You can only view certificates for your assigned batches.")
            
    return render(request, 'certificates/certificate_detail.html', {
        'certificate': certificate,
        'is_admin': is_admin
    })


@login_required
def certificate_revoke(request, pk):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")
    certificate = get_object_or_404(Certificate, pk=pk)
    certificate.status = 'revoked'
    certificate.save()
    messages.success(request, f"Certificate {certificate.certificate_number} has been revoked successfully.")
    return redirect('certificate_detail', pk=certificate.pk)


@login_required
def certificate_delete(request, pk):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")
    certificate = get_object_or_404(Certificate, pk=pk)
    if request.method == 'POST':
        certificate.delete()
        messages.success(request, "Certificate deleted successfully.")
        return redirect('certificate_list')
        
    return render(request, 'certificates/certificate_confirm_delete.html', {
        'certificate': certificate
    })
