from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now

from apps.exams.models import Exam, StudentExamAttempt, StudentAnswer, Option
from apps.students.models import StudentProfile, StudentAdmission
from apps.students.forms import StudentProfileForm, StudentAdmissionForm
from apps.accounts.views import admin_required


# ---------------------------------------------------------------------------
# Student Dashboard
# ---------------------------------------------------------------------------

@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('login')

    attempts = StudentExamAttempt.objects.filter(student=request.user)
    total_attempts = attempts.count()
    average_score = sum(a.score for a in attempts) / total_attempts if total_attempts > 0 else 0

    try:
        profile = request.user.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        profile = None
        batch = None

    if batch:
        total_exams = Exam.objects.filter(is_published=True, batches=batch).count()
    else:
        total_exams = 0

    # Fee Calculations
    from django.db.models import Sum
    from apps.fees.models import FeePayment
    from decimal import Decimal

    course_fee = 0.00
    paid_amount = 0.00
    pending_amount = 0.00
    fee_status = 'PENDING'

    if profile:
        if batch and batch.course:
            course_fee = batch.course.fees
        paid_amount = FeePayment.objects.filter(student=profile).aggregate(total=Sum('amount'))['total'] or 0.00
        
        course_fee = Decimal(str(course_fee))
        paid_amount = Decimal(str(paid_amount))
        pending_amount = course_fee - paid_amount
        
        if paid_amount == 0:
            fee_status = 'PENDING'
        elif pending_amount <= 0:
            fee_status = 'PAID'
        else:
            fee_status = 'PARTIAL'

    # Certificate Calculations
    from apps.certificates.models import Certificate
    from apps.certificates.views import get_student_eligibility
    from django.db.models import Q

    certificates = []
    issued_certificates_count = 0
    eligibility = {'eligible': False, 'reason': 'No student profile.'}

    if profile:
        admission = StudentAdmission.objects.filter(
            Q(enrollment_no=request.user.username) | Q(email=profile.email)
        ).first()
        if admission:
            certificates = Certificate.objects.filter(student=admission)
            issued_certificates_count = certificates.count()
        eligibility = get_student_eligibility(profile)

    context = {
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'average_score': round(average_score, 1),
        'course_fee': course_fee,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'fee_status': fee_status,
        'certificates': certificates,
        'issued_certificates_count': issued_certificates_count,
        'eligibility': eligibility,
    }
    return render(request, 'student/student_dashboard.html', context)


# ---------------------------------------------------------------------------
# Exam browsing & instructions
# ---------------------------------------------------------------------------

@login_required
def student_exam_list(request):
    if request.user.role != 'student':
        return redirect('login')

    try:
        profile = request.user.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        batch = None

    if batch:
        exams = Exam.objects.filter(is_published=True, batches=batch)
    else:
        exams = Exam.objects.none()

    return render(request, 'student/student_exam_list.html', {'exams': exams})


@login_required
def exam_instructions_view(request, exam_id):
    if request.user.role != 'student':
        return redirect('login')

    try:
        profile = request.user.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        batch = None

    if not batch:
        return HttpResponseForbidden("You do not belong to any batch.")

    exam = get_object_or_404(Exam, id=exam_id, batches=batch, is_published=True)

    attempts = StudentExamAttempt.objects.filter(student=request.user, exam=exam)
    latest_attempt = attempts.order_by('-submitted_at').first()
    in_progress_attempt = attempts.filter(is_completed=False).first()
    completed_attempt = attempts.filter(is_completed=True).order_by('-submitted_at').first()

    is_closed = exam.end_date and now() > exam.end_date and not in_progress_attempt
    can_start = not is_closed and (not completed_attempt or exam.allow_retake or in_progress_attempt)

    return render(request, 'student/exam_instructions.html', {
        'exam': exam,
        'latest_attempt': latest_attempt,
        'is_closed': is_closed,
        'can_start': can_start,
    })


# ---------------------------------------------------------------------------
# Exam attempt & submit
# ---------------------------------------------------------------------------

@login_required
def attempt_exam(request, exam_id):
    if request.user.role != 'student':
        return redirect('login')

    try:
        profile = request.user.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        batch = None

    if not batch:
        return HttpResponseForbidden("You do not belong to any batch.")

    exam = get_object_or_404(Exam, id=exam_id, batches=batch, is_published=True)

    attempts = StudentExamAttempt.objects.filter(student=request.user, exam=exam)
    in_progress_attempt = attempts.filter(is_completed=False).order_by('-start_time').first()
    completed_attempt = attempts.filter(is_completed=True).order_by('-submitted_at').first()

    # SECURITY CHECK 1: Already completed and retakes not allowed
    if completed_attempt and not in_progress_attempt and not exam.allow_retake:
        messages.warning(request, "You have already completed this exam.")
        return redirect('student_exam_result', attempt_id=completed_attempt.id)

    # SECURITY CHECK 2: Past deadline for new attempts
    if exam.end_date and now() > exam.end_date and not in_progress_attempt:
        messages.error(request, "This exam is closed and no longer accepts new attempts.")
        return redirect('exam_instructions', exam_id=exam.id)

    # Start the clock: create attempt if needed
    attempt = in_progress_attempt or StudentExamAttempt.objects.create(student=request.user, exam=exam)

    questions = exam.questions.all().order_by('?')
    total_marks = sum(question.marks for question in questions)

    # Calculate remaining seconds from server time
    elapsed_time = (now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, (exam.duration_minutes * 60) - elapsed_time)

    # Time expired while tab was closed
    if remaining_seconds <= 0:
        messages.error(request, "Your time for this exam has expired.")
        attempt.is_completed = True
        attempt.save()
        return redirect('student_exam_result', attempt_id=attempt.id)

    return render(request, 'exam/attempt_exam.html', {
        'exam': exam,
        'questions': questions,
        'total_marks': total_marks,
        'remaining_seconds': remaining_seconds,
    })


@login_required
def submit_exam(request, exam_id):
    if request.method == 'POST':
        if request.user.role != 'student':
            return redirect('login')

        try:
            profile = request.user.studentprofile
            batch = profile.batch
        except StudentProfile.DoesNotExist:
            batch = None

        if not batch:
            return HttpResponseForbidden("You do not belong to any batch.")

        exam = get_object_or_404(Exam, id=exam_id, batches=batch, is_published=True)
        student = request.user
        attempt = StudentExamAttempt.objects.filter(
            student=student, exam=exam, is_completed=False
        ).order_by('-start_time').first()

        if not attempt:
            messages.warning(request, "No active exam attempt found.")
            return redirect('student_exam_list')

        # Time validation check
        elapsed_time = (now() - attempt.start_time).total_seconds()
        allowed_time = (exam.duration_minutes * 60) + 60

        if elapsed_time > allowed_time:
            messages.error(request, "Time expired! Your submission was rejected.")
            attempt.is_completed = True
            attempt.save()
            return redirect('student_exam_result', attempt_id=attempt.id)

        # --- GRADING LOGIC (marks-weighted, with negative marking) ---
        total_marks = sum(question.marks for question in exam.questions.all())
        marks_earned = 0

        for question in exam.questions.all():
            selected_option_id = request.POST.get(str(question.id))

            if selected_option_id:
                try:
                    selected_option = Option.objects.get(id=selected_option_id)
                    StudentAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_option
                    )
                    if selected_option.is_correct:
                        marks_earned += question.marks
                    else:
                        marks_earned -= exam.negative_marks
                except Option.DoesNotExist:
                    pass

        marks_earned = max(0, marks_earned)
        score = (marks_earned / total_marks) * 100 if total_marks > 0 else 0
        attempt.score = score
        attempt.is_completed = True
        attempt.save()

        messages.success(request, "Exam submitted successfully!")
        return redirect('student_exam_result', attempt_id=attempt.id)
    else:
        return redirect('student_exam_list')


# ---------------------------------------------------------------------------
# Results & History
# ---------------------------------------------------------------------------

@login_required
def student_exam_result(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)
    answers = attempt.answers.all()

    total_marks = sum(question.marks for question in attempt.exam.questions.all())

    marks_earned = 0
    for ans in answers:
        if ans.selected_option:
            if ans.selected_option.is_correct:
                marks_earned += ans.question.marks
            else:
                marks_earned -= attempt.exam.negative_marks
    marks_earned = max(0, marks_earned)

    rounded_score = int(round(attempt.score))
    progress_width = f"width: {rounded_score}%;"
    passed = attempt.score >= attempt.exam.pass_percentage

    return render(request, 'student/student_exam_result.html', {
        'attempt': attempt,
        'answers': answers,
        'total_marks': total_marks,
        'marks_earned': marks_earned,
        'rounded_score': rounded_score,
        'progress_width': progress_width,
        'passed': passed,
    })


@login_required
def student_exam_history(request):
    attempts = StudentExamAttempt.objects.filter(student=request.user).order_by('-submitted_at')
    return render(request, 'student/student_exam_history.html', {'attempts': attempts})


@login_required
def delete_student_exam_attempt(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)

    if request.method == 'POST':
        attempt.delete()
        messages.success(request, "Exam attempt deleted successfully.")
        return redirect('student_exam_history')

    return render(request, 'student/confirm_delete_attempt.html', {'attempt': attempt})


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------

@login_required
def student_profile(request):
    from django.db.models import Q
    from django.contrib.auth import get_user_model

    is_admin_or_center = request.user.role in ['admin', 'center']
    student_id = request.GET.get('student_id')
    admission = None
    profile = None

    if is_admin_or_center and student_id:
        try:
            admission = StudentAdmission.objects.select_related('course', 'center').get(id=student_id)
            profile = StudentProfile.objects.filter(user__username=admission.enrollment_no).first()
            if not profile and admission.email:
                profile = StudentProfile.objects.filter(email=admission.email).first()
        except StudentAdmission.DoesNotExist:
            pass

    if not admission:
        student = request.user
        try:
            profile = student.studentprofile
            admission = StudentAdmission.objects.select_related('course', 'center').filter(
                Q(enrollment_no=student.username) | Q(email=profile.email)
            ).first()
        except StudentProfile.DoesNotExist:
            profile = None
            admission = StudentAdmission.objects.select_related('course', 'center').filter(enrollment_no=student.username).first()

    base_template = 'accounts/admin_dashboard.html' if is_admin_or_center else 'accounts/base.html'

    attempts = []
    if profile:
        attempts = StudentExamAttempt.objects.filter(student=profile.user)
    elif admission:
        User = get_user_model()
        user_obj = User.objects.filter(username=admission.enrollment_no).first()
        if user_obj:
            attempts = StudentExamAttempt.objects.filter(student=user_obj)

    total_attempts = len(attempts)
    if total_attempts > 0:
        average_score = sum(a.score for a in attempts) / total_attempts
    else:
        average_score = 0

    present_days = 0
    absent_days = 0
    attendance_percentage = 0.0
    recent_attendances = []

    course_fee = 0.00
    paid_amount = 0.00
    pending_amount = 0.00
    fee_status = 'PENDING'

    if profile:
        from apps.attendance.models import Attendance
        student_attendances = Attendance.objects.filter(student=profile)
        present_days = student_attendances.filter(status='present').count()
        absent_days = student_attendances.filter(status='absent').count()
        total_days = present_days + absent_days
        if total_days > 0:
            attendance_percentage = round((present_days / total_days) * 100, 1)
        recent_attendances = student_attendances.order_by('-date')[:5]

    # Fee calculations
    from django.db.models import Sum
    from apps.fees.models import FeePayment
    from decimal import Decimal

    if admission and admission.course:
        course_fee = admission.course.fees
    elif profile and profile.batch and profile.batch.course:
        course_fee = profile.batch.course.fees

    target_profile = profile
    if admission and not target_profile:
        target_profile = StudentProfile.objects.filter(user__username=admission.enrollment_no).first()
        if not target_profile and admission.email:
            target_profile = StudentProfile.objects.filter(email=admission.email).first()

    if target_profile:
        paid_amount = FeePayment.objects.filter(student=target_profile).aggregate(total=Sum('amount'))['total'] or 0.00
    else:
        paid_amount = 0.00

    course_fee = Decimal(str(course_fee)) if course_fee else Decimal('0.00')
    paid_amount = Decimal(str(paid_amount))
    pending_amount = course_fee - paid_amount

    if paid_amount == 0:
        fee_status = 'PENDING'
    elif pending_amount <= 0:
        fee_status = 'PAID'
    else:
        fee_status = 'PARTIAL'

    # Certificate calculations
    from apps.certificates.models import Certificate
    from apps.certificates.views import get_student_eligibility
    
    if admission:
        student_certificates = Certificate.objects.filter(student=admission)
        issued_count = student_certificates.count()
    else:
        student_certificates = []
        issued_count = 0

    if target_profile:
        eligibility = get_student_eligibility(target_profile)
    else:
        eligibility = {'eligible': False, 'reason': 'No student profile.'}

    template_name = 'student/student_profile_admin.html' if is_admin_or_center else 'student/student_profile.html'

    return render(request, template_name, {
        'student': profile.user if profile else None,
        'profile': profile,
        'admission': admission,
        'base_template': base_template,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'average_score': round(average_score, 2),
        'present_days': present_days,
        'absent_days': absent_days,
        'attendance_percentage': attendance_percentage,
        'recent_attendances': recent_attendances,
        'course_fee': course_fee,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'fee_status': fee_status,
        'certificates': student_certificates,
        'issued_certificates_count': issued_count,
        'eligibility': eligibility,
    })



@login_required
def edit_student_profile(request):
    profile, created = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('student_profile')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'student/edit_profile.html', {'form': form})


@admin_required
def student_admission_view(request):
    if request.method == 'POST':
        form = StudentAdmissionForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student Admission processed successfully.')
            return redirect('student_admission')
    else:
        form = StudentAdmissionForm()
    
    return render(request, 'student/student_admission.html', {'form': form})


# ---------------------------------------------------------------------------
# Student Details — Search & Quick Profile
# ---------------------------------------------------------------------------

@admin_required
def student_details_view(request):
    """Search student by enrollment no / name / mobile and display quick profile."""
    from django.http import JsonResponse
    from django.db.models import Q

    student = None
    admission = None
    error = None

    enrollment = request.GET.get('enrollment', '').strip()
    if enrollment:
        try:
            admission = (
                StudentAdmission.objects
                .select_related('center', 'course')
                .get(enrollment_no=enrollment)
            )
        except StudentAdmission.DoesNotExist:
            error = 'No student found with that Enrollment Number / Name / Mobile.'

    return render(request, 'student/student_details.html', {
        'admission': admission,
        'error': error,
        'enrollment': enrollment,
    })


@login_required
def student_search_autocomplete(request):
    """Return JSON list of students matching query for Select2 autocomplete."""
    from django.http import JsonResponse
    from django.db.models import Q

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        qs = (
            StudentAdmission.objects
            .filter(
                Q(enrollment_no__icontains=q) |
                Q(student_name__icontains=q) |
                Q(whatsapp_no__icontains=q)
            )
            .select_related('center')
            .order_by('student_name')[:20]
        )
        for s in qs:
            photo_url = s.photo.url if s.photo else ''
            results.append({
                'id': s.enrollment_no, # Used by Student Details
                'db_id': s.id,         # Used by ID Card
                'text': f'{s.student_name} ({s.enrollment_no})',
                'name': s.student_name,
                'enrollment': s.enrollment_no,
                'mobile': s.whatsapp_no,
                'photo': photo_url,
            })
    return JsonResponse({'results': results})


# ---------------------------------------------------------------------------
# Student ID Card
# ---------------------------------------------------------------------------

@login_required
def student_id_card_view(request):
    """Search student and display ID card preview for printing."""
    student_id = request.GET.get('student_id', '').strip()
    admission = None
    error = None

    if student_id:
        try:
            admission = (
                StudentAdmission.objects
                .select_related('center', 'course')
                .get(pk=student_id)
            )
        except StudentAdmission.DoesNotExist:
            error = 'No student found with that ID.'
        except ValueError:
            error = 'Invalid Student ID provided.'

    return render(request, 'student/student_id_card.html', {
        'admission': admission,
        'error': error,
    })


# ---------------------------------------------------------------------------
# Pending List (Admission Verification Queue)
# ---------------------------------------------------------------------------

@login_required
def student_pending_list(request):
    """List pending student admissions. Admins see all, Center sees own."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Permission check: Only Admin and Center allowed
    if request.user.role not in ['admin', 'center']:
        return redirect('student_dashboard')

    qs = StudentAdmission.objects.filter(status='Pending').select_related('center', 'course')

    if request.user.role == 'center':
        qs = qs.filter(center__code=request.user.username)  # Center can only see their own admissions

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(enrollment_no__icontains=q) |
            Q(student_name__icontains=q) |
            Q(whatsapp_no__icontains=q) |
            Q(email__icontains=q)
        )

    # Ordering: Newest first
    qs = qs.order_by('-created_at', '-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'student/pending_list.html', {
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
    })


@login_required
def student_approve_action(request, pk):
    """Approve a pending or cancelled student admission."""
    from django.utils import timezone
    
    redirect_url = request.META.get('HTTP_REFERER') or 'student_pending_list'
    
    if request.method == 'POST':
        if request.user.role not in ['admin', 'center']:
            messages.error(request, 'Permission denied.')
            return redirect(redirect_url)
            
        try:
            admission = StudentAdmission.objects.get(pk=pk, status__in=['Pending', 'Cancelled'])
            
            # Center can only approve own students
            if request.user.role == 'center' and admission.center and admission.center.code != request.user.username:
                messages.error(request, 'Permission denied.')
                return redirect(redirect_url)

            admission.status = 'Approved'
            admission.approved_by = request.user
            admission.approved_at = timezone.now()
            admission.cancelled_by = None
            admission.cancelled_at = None
            admission.cancel_reason = None
            admission.save()
            messages.success(request, 'Student Admission Approved Successfully.')
            
        except StudentAdmission.DoesNotExist:
            messages.error(request, 'Admission not found or is already Approved.')

    return redirect(redirect_url)


@login_required
def student_cancel_action(request, pk):
    """Cancel a pending student admission or update cancelled details."""
    from django.utils import timezone
    
    redirect_url = request.META.get('HTTP_REFERER') or 'student_pending_list'
    
    if request.method == 'POST':
        if request.user.role not in ['admin', 'center']:
            messages.error(request, 'Permission denied.')
            return redirect(redirect_url)
            
        try:
            admission = StudentAdmission.objects.get(pk=pk, status__in=['Pending', 'Cancelled'])
            
            # Center can only cancel own students
            if request.user.role == 'center' and admission.center and admission.center.code != request.user.username:
                messages.error(request, 'Permission denied.')
                return redirect(redirect_url)

            cancel_reason = request.POST.get('cancel_reason', '').strip()
            
            admission.status = 'Cancelled'
            admission.cancelled_by = request.user
            admission.cancelled_at = timezone.now()
            admission.cancel_reason = cancel_reason
            admission.approved_by = None
            admission.approved_at = None
            admission.save()
            messages.success(request, 'Student Admission Cancelled.')
            
        except StudentAdmission.DoesNotExist:
            messages.error(request, 'Admission not found or is already Approved.')

    return redirect(redirect_url)


# ---------------------------------------------------------------------------
# Approved List & Cancel List
# ---------------------------------------------------------------------------

@login_required
def student_approved_list(request):
    """List approved student admissions. Admins see all, Center sees own."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Permission check: Only Admin and Center allowed
    if request.user.role not in ['admin', 'center']:
        return redirect('student_dashboard')

    qs = StudentAdmission.objects.filter(status='Approved').select_related('center', 'course')

    if request.user.role == 'center':
        qs = qs.filter(center__code=request.user.username)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(enrollment_no__icontains=q) |
            Q(student_name__icontains=q) |
            Q(whatsapp_no__icontains=q) |
            Q(email__icontains=q)
        )

    # Ordering: Newest first
    qs = qs.order_by('-created_at', '-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'student/approved_list.html', {
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
    })


@login_required
def student_cancelled_list(request):
    """List cancelled student admissions. Admins see all, Center sees own."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    # Permission check: Only Admin and Center allowed
    if request.user.role not in ['admin', 'center']:
        return redirect('student_dashboard')

    qs = StudentAdmission.objects.filter(status='Cancelled').select_related('center', 'course')

    if request.user.role == 'center':
        qs = qs.filter(center__code=request.user.username)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(enrollment_no__icontains=q) |
            Q(student_name__icontains=q) |
            Q(whatsapp_no__icontains=q) |
            Q(email__icontains=q)
        )

    # Ordering: Newest first
    qs = qs.order_by('-created_at', '-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'student/cancelled_list.html', {
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
    })


@login_required
def student_revert_pending_action(request, pk):
    """Revert an approved or cancelled student admission back to pending."""
    if request.method == 'POST':
        if request.user.role not in ['admin', 'center']:
            messages.error(request, 'Permission denied.')
            return redirect('student_approved_list')
            
        try:
            admission = StudentAdmission.objects.get(pk=pk)
            
            # Center can only revert own students
            if request.user.role == 'center' and admission.center and admission.center.code != request.user.username:
                messages.error(request, 'Permission denied.')
                return redirect('student_approved_list')

            admission.status = 'Pending'
            admission.approved_by = None
            admission.approved_at = None
            admission.cancelled_by = None
            admission.cancelled_at = None
            admission.cancel_reason = None
            admission.save()
            messages.success(request, 'Student Admission Reverted to Pending.')
            
        except StudentAdmission.DoesNotExist:
            messages.error(request, 'Admission record not found.')

    return redirect('student_approved_list')


@login_required
def student_list_by_center(request):
    """List students filtered by Selected Center."""
    from apps.centers.models import Center
    from django.db.models import Q
    from django.core.paginator import Paginator
    from django.contrib import messages
    
    # Check permissions (only admin and center role can view, center role is locked to their own center)
    if request.user.role not in ['admin', 'center']:
        messages.error(request, 'Permission denied.')
        return redirect('admin_dashboard')
        
    centers = Center.objects.all().order_by('name')
    selected_center_id = request.GET.get('center_id', '').strip()
    
    # If the user is a center, force selected_center_id to be their own center
    if request.user.role == 'center':
        try:
            user_center = Center.objects.get(code=request.user.username)
            selected_center_id = str(user_center.id)
            # Filter centers list to only their own center for center role
            centers = centers.filter(id=user_center.id)
        except Center.DoesNotExist:
            messages.error(request, 'Center not found for your account.')
            return redirect('admin_dashboard')
            
    qs = StudentAdmission.objects.select_related('course', 'center').all()
    
    if selected_center_id:
        qs = qs.filter(center_id=selected_center_id)
    else:
        # If admin and no center is selected, display empty list
        if request.user.role == 'admin':
            qs = qs.none()
            
    # Search query within the filtered queryset
    q = request.GET.get('q', '').strip()
    if q and selected_center_id:
        qs = qs.filter(
            Q(enrollment_no__icontains=q) |
            Q(student_name__icontains=q) |
            Q(whatsapp_no__icontains=q) |
            Q(email__icontains=q)
        )
        
    # Ordering: Newest first
    qs = qs.order_by('-created_at', '-id')
    
    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10
        
    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'student/list_by_center.html', {
        'centers': centers,
        'selected_center_id': selected_center_id,
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
    })


@login_required
def passout_student_list(request):
    """List students who have been issued certificates (passout students)."""
    from django.core.paginator import Paginator
    from django.db.models import Q
    from apps.certificates.models import Certificate
    
    # Permission check: Only Admin and Center allowed
    if request.user.role not in ['admin', 'center']:
        return redirect('student_dashboard')

    qs = Certificate.objects.select_related('student', 'center', 'course').all()

    if request.user.role == 'center':
        qs = qs.filter(center=request.user.center)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(student__enrollment_no__icontains=q) |
            Q(student__student_name__icontains=q) |
            Q(student__whatsapp_no__icontains=q) |
            Q(student__email__icontains=q) |
            Q(course__name__icontains=q)
        )

    # Export (CSV)
    if request.GET.get('export') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="passout_students.csv"'
        writer = csv.writer(response)
        writer.writerow(['Enrollment No', 'Name', 'Contact', 'Email', 'Course', 'Course Duration'])
        for item in qs:
            writer.writerow([
                item.student.enrollment_no,
                item.student.student_name,
                item.student.whatsapp_no,
                item.student.email or '-',
                item.course.name,
                item.course_duration or '-'
            ])
        return response

    # Ordering
    qs = qs.order_by('-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'student/passout_student_list.html', {
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
    })


