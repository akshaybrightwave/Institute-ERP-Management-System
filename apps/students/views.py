from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.utils.dateparse import parse_date

from apps.exams.models import Exam, StudentExamAttempt, StudentAnswer, Option
from apps.students.models import StudentProfile, StudentAdmission
from apps.students.forms import StudentProfileForm, StudentAdmissionForm
from apps.fees.forms import FeePaymentForm
from apps.accounts.views import admin_required


# ---------------------------------------------------------------------------
# Student Dashboard Helper & View
# ---------------------------------------------------------------------------

def get_fee_emis(course_fee, paid_amount):
    """
    Generates installment schedule. Let's divide course fee into 4 equal monthly installments.
    """
    from decimal import Decimal
    course_fee = Decimal(str(course_fee))
    paid_amount = Decimal(str(paid_amount))
    
    if course_fee <= 0:
        return []
        
    num_installments = 4
    inst_amount = (course_fee / num_installments).quantize(Decimal('0.01'))
    
    emis = []
    accumulated_paid = paid_amount
    
    for i in range(1, num_installments + 1):
        # Last installment handles rounding differences
        amt = inst_amount if i < num_installments else (course_fee - inst_amount * (num_installments - 1))
        
        if accumulated_paid >= amt:
            status = 'Paid'
            paid_amt = amt
            accumulated_paid -= amt
        elif accumulated_paid > 0:
            status = 'Partially Paid'
            paid_amt = accumulated_paid
            accumulated_paid = Decimal('0.00')
        else:
            status = 'Pending'
            paid_amt = Decimal('0.00')
            
        emis.append({
            'installment_no': i,
            'amount': amt,
            'paid_amount': paid_amt,
            'status': status,
            'due_date': f"Month {i}"
        })
    return emis


@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('login')

    from django.db.models import Sum, Q
    from apps.fees.models import FeePayment
    from apps.certificates.models import Certificate
    from apps.certificates.views import get_student_eligibility
    from apps.attendance.models import Attendance
    from decimal import Decimal
    from django.contrib import messages
    from django.contrib.auth.forms import SetPasswordForm
    from django.contrib.auth import update_session_auth_hash

    # 1. Fetch Profile & Admission info
    admission = StudentAdmission.objects.select_related('course', 'center').filter(user=request.user).first()

    try:
        profile = StudentProfile.objects.select_related('batch__course', 'batch__center').get(user=request.user)
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        profile = None
        batch = None

    # 2. Exam calculations
    attempts = StudentExamAttempt.objects.filter(student=request.user)
    total_attempts = attempts.count()
    average_score = sum(a.score for a in attempts) / total_attempts if total_attempts > 0 else 0

    if batch:
        total_exams = Exam.objects.filter(is_published=True, batches=batch).count()
    else:
        total_exams = 0

    # 3. Fee Calculations
    course_fee = Decimal('0.00')
    paid_amount = Decimal('0.00')
    pending_amount = Decimal('0.00')
    fee_status = 'PENDING'
    fee_payments = []

    if admission and admission.course:
        course_fee = Decimal(str(admission.course.fees))

    if profile:
        
        # Get all payments
        fee_payments = FeePayment.objects.filter(student=profile).select_related('student__batch__course').order_by('-payment_date', '-id')
        paid_amount = fee_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        paid_amount = Decimal(str(paid_amount))
        pending_amount = course_fee - paid_amount
        
        if paid_amount == 0:
            fee_status = 'PENDING'
        elif pending_amount <= 0:
            fee_status = 'PAID'
        else:
            fee_status = 'PARTIAL'

    # EMI Schedule
    emis = get_fee_emis(course_fee, paid_amount)

    # 4. Certificate Calculations
    certificates = []
    issued_certificates_count = 0
    eligibility = {'eligible': False, 'reason': 'No student profile.'}

    if admission:
        certificates = Certificate.objects.filter(student=admission)
        issued_certificates_count = certificates.count()
    if profile:
        eligibility = get_student_eligibility(profile)

    # 5. Change Password Form
    password_form = SetPasswordForm(request.user)
    requested_tab = request.GET.get('tab', '')
    active_profile_tab = requested_tab if requested_tab in {'fees', 'overview', 'password', 'notifications'} else ''
    if request.method == 'POST' and request.POST.get('action') == 'change_password':
        active_profile_tab = 'password'
        password_form = SetPasswordForm(request.user, {
            'new_password1': request.POST.get('new_password', ''),
            'new_password2': request.POST.get('confirm_password', ''),
        })
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect(f"{request.path}#password")
        else:
            messages.error(request, 'Please correct the error below.')

    # 6. Notifications
    notifications = [
        {
            'title': 'Welcome to Examly!',
            'message': 'Welcome to your student portal. Here you can view your profile, download your ID card, view attendance, download admit cards, check marksheets, and attempt exams.',
            'date': 'Just now',
            'icon': 'bi-bell-fill text-primary'
        },
        {
            'title': 'Exam System Guidelines',
            'message': 'Make sure you have a stable internet connection before starting any online exam.',
            'date': '1 day ago',
            'icon': 'bi-info-circle-fill text-info'
        }
    ]

    context = {
        'profile': profile,
        'admission': admission,
        'total_exams': total_exams,
        'total_attempts': total_attempts,
        'average_score': round(average_score, 1),
        'course_fee': course_fee,
        'paid_amount': paid_amount,
        'pending_amount': pending_amount,
        'fee_status': fee_status,
        'fee_payments': fee_payments,
        'emis': emis,
        'certificates': certificates,
        'issued_certificates_count': issued_certificates_count,
        'eligibility': eligibility,
        'password_form': password_form,
        'notifications': notifications,
        'active_profile_tab': active_profile_tab,
    }
    return render(request, 'student/student_dashboard.html', context)


# ---------------------------------------------------------------------------
# Exam browsing & instructions
# ---------------------------------------------------------------------------

def get_student_exam_queryset(user):
    from django.db.models import Q
    from apps.exams.models import Exam, ExamCenterAssignment
    from apps.students.models import StudentAdmission, StudentProfile

    admission = StudentAdmission.objects.select_related('center', 'course').filter(user=user).first()
    if not admission:
        return Exam.objects.none()

    try:
        profile = user.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        batch = None

    qs = Exam.objects.filter(is_published=True).select_related('course').prefetch_related('batches')

    center_assigned_exam_ids = ExamCenterAssignment.objects.filter(
        center=admission.center,
        status=True,
        is_deleted=False
    ).values_list('exam_id', flat=True)

    # Center security check
    qs = qs.filter(
        Q(center=admission.center) |
        Q(center__isnull=True, center_assignments__isnull=True) |
        Q(id__in=center_assigned_exam_ids)
    )

    # Assignment condition: direct, batch, or course
    assignment_q = Q(student_assignments__student=admission, student_assignments__status=True, student_assignments__is_deleted=False)
    if batch:
        assignment_q |= Q(batches=batch, center_assignments__isnull=True)
    if admission.course:
        assignment_q |= Q(course=admission.course, center_assignments__isnull=True)

    return qs.filter(assignment_q).distinct()


@login_required
def student_exam_list(request):
    if request.user.role != 'student':
        return redirect('login')

    exams = get_student_exam_queryset(request.user)
    
    from apps.exams.models import StudentExamAttempt
    from django.utils.timezone import now
    current_time = now()
    
    attempts = StudentExamAttempt.objects.filter(student=request.user)
    completed_exam_ids = set(attempts.filter(is_completed=True).values_list('exam_id', flat=True))
    in_progress_exam_ids = set(attempts.filter(is_completed=False).values_list('exam_id', flat=True))
    
    for exam in exams:
        if exam.id in completed_exam_ids:
            if exam.allow_retake:
                exam.status_label = "Completed (Retake Available)"
                exam.status_class = "success"
                exam.action_label = "Reattempt"
            else:
                exam.status_label = "Completed"
                exam.status_class = "secondary"
                exam.action_label = "View"
        elif exam.id in in_progress_exam_ids:
            exam.status_label = "In Progress"
            exam.status_class = "warning text-dark"
            exam.action_label = "Resume"
        else:
            if exam.end_date and current_time > exam.end_date:
                exam.status_label = "Expired"
                exam.status_class = "danger"
                exam.action_label = "View"
            else:
                exam.status_label = "Available"
                exam.status_class = "primary"
                exam.action_label = "Start Exam"
                
    return render(request, 'student/student_exam_list.html', {'exams': exams})


@login_required
def exam_instructions_view(request, exam_id):
    if request.user.role != 'student':
        return redirect('login')

    admission = StudentAdmission.objects.select_related('center').filter(user=request.user).first()
    if not admission:
        return HttpResponseForbidden("Access Denied: No student admission record found.")

    exam = get_object_or_404(get_student_exam_queryset(request.user), id=exam_id)

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

    admission = StudentAdmission.objects.select_related('center').filter(user=request.user).first()
    if not admission:
        return HttpResponseForbidden("Access Denied: No student admission record found.")

    exam = get_object_or_404(get_student_exam_queryset(request.user), id=exam_id)

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

    # Start the clock: create attempt if needed. For a new retake, charge the
    # student's center wallet once before creating the new attempt.
    if in_progress_attempt:
        attempt = in_progress_attempt
    else:
        if completed_attempt and exam.allow_retake:
            if not admission.center:
                messages.error(request, "Re-exam cannot start because your admission is not linked to a center.")
                return redirect('exam_instructions', exam_id=exam.id)

            from django.db import transaction
            from apps.fees.services import deduct_center_wallet_for_student_fee

            try:
                with transaction.atomic():
                    deducted_amount = deduct_center_wallet_for_student_fee(admission.center, 'Re-Exam Fees')
                    attempt = StudentExamAttempt.objects.create(student=request.user, exam=exam)
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect('exam_instructions', exam_id=exam.id)

            if deducted_amount > 0:
                messages.success(request, f"Re-exam fee Rs.{deducted_amount:.2f} deducted from center wallet.")
        else:
            attempt = StudentExamAttempt.objects.create(student=request.user, exam=exam)

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

        admission = StudentAdmission.objects.select_related('center').filter(user=request.user).first()
        if not admission:
            return HttpResponseForbidden("Access Denied: No student admission record found.")

        exam = get_object_or_404(get_student_exam_queryset(request.user), id=exam_id)
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
    from apps.students.models import StudentAdmission, StudentProfile
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id)

    # Role Based Access Validation
    role = request.user.role
    if role == 'student':
        if attempt.student != request.user:
            return HttpResponseForbidden("Access Denied: You cannot view other students' results.")
    elif role == 'center':
        student_admission = getattr(attempt.student, 'student_admission', None)
        student_profile = getattr(attempt.student, 'studentprofile', None)
        is_owner = False
        if student_admission and student_admission.center == request.user.center:
            is_owner = True
        elif student_profile and student_profile.batch and student_profile.batch.center == request.user.center:
            is_owner = True
        if not is_owner:
            return HttpResponseForbidden("Access Denied: You cannot view other centers' student results.")
    elif role == 'admin':
        pass
    else:
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    answers = attempt.answers.select_related('question', 'selected_option').prefetch_related('question__options')

    admission = StudentAdmission.objects.select_related('course', 'center').filter(user=attempt.student).first()
    try:
        profile = attempt.student.studentprofile
        batch = profile.batch
    except StudentProfile.DoesNotExist:
        profile = None
        batch = None

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

    # Answer stats
    attempted_questions = answers.filter(selected_option__isnull=False).count()
    correct_answers = answers.filter(selected_option__is_correct=True).count()
    wrong_answers = answers.filter(selected_option__is_correct=False).count()
    total_questions = attempt.exam.questions.count()

    return render(request, 'student/student_exam_result.html', {
        'attempt': attempt,
        'answers': answers,
        'admission': admission,
        'batch': batch,
        'total_marks': total_marks,
        'marks_earned': marks_earned,
        'rounded_score': rounded_score,
        'progress_width': progress_width,
        'passed': passed,
        'attempted_questions': attempted_questions,
        'correct_answers': correct_answers,
        'wrong_answers': wrong_answers,
        'total_questions': total_questions,
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
    if request.user.role == 'student':
        return student_dashboard(request)

    from django.db.models import Q
    from django.contrib.auth import get_user_model

    is_admin_or_center = request.user.role in ['admin', 'center']
    student_id = request.GET.get('student_id')
    admission = None
    profile = None

    if is_admin_or_center and student_id:
        try:
            admission = StudentAdmission.objects.select_related('course', 'center', 'user').get(id=student_id)
            if admission.user:
                profile = getattr(admission.user, 'studentprofile', None)
            if not profile:
                profile = StudentProfile.objects.filter(user__username=admission.enrollment_no).first()
            if not profile and admission.email:
                profile = StudentProfile.objects.filter(email=admission.email).first()
        except StudentAdmission.DoesNotExist:
            pass

    if not admission:
        student = request.user
        admission = StudentAdmission.objects.select_related('course', 'center', 'user').filter(user=student).first()
        try:
            profile = student.studentprofile
        except StudentProfile.DoesNotExist:
            profile = None

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

    if admission:
        from apps.attendance.models import Attendance
        student_attendances = Attendance.objects.filter(student=admission)
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

    if profile and profile.course_fee_at_admission is not None:
        course_fee = profile.course_fee_at_admission
    elif admission and admission.course:
        course_fee = admission.course.fees
    elif profile and profile.batch and profile.batch.course:
        course_fee = profile.batch.course.fees

    fee_payments = []
    target_profile = profile
    if admission and not target_profile:
        target_profile = StudentProfile.objects.filter(user__username=admission.enrollment_no).first()
        if not target_profile and admission.email:
            target_profile = StudentProfile.objects.filter(email=admission.email).first()

    fee_payment_form = None
    show_fee_payment_form = False
    fee_payment_action = 'add_fee_payment'
    editing_fee_payment = None
    active_profile_tab = ''

    profile_base_url = f"{request.path}?student_id={admission.pk}" if admission else request.path

    if is_admin_or_center and admission and request.method == 'POST' and request.POST.get('action') == 'update_student_account':
        editable_fields = [
            'student_name', 'gender', 'status', 'whatsapp_no', 'alt_mobile', 'aadhar_no',
            'email', 'father_name', 'mother_name', 'family_id', 'address', 'pincode',
            'state', 'district', 'marital_status', 'category', 'medium',
        ]
        for field in editable_fields:
            setattr(admission, field, request.POST.get(field, '').strip())

        dob = parse_date(request.POST.get('dob', ''))
        admission.dob = dob
        admission.save(update_fields=editable_fields + ['dob'])

        if profile:
            profile.full_name = admission.student_name
            profile.email = admission.email or profile.email
            profile.phone = admission.whatsapp_no
            profile.save(update_fields=['full_name', 'email', 'phone'])

        messages.success(request, "Student account details updated successfully.")
        return redirect(f"{profile_base_url}#update")

    if is_admin_or_center and admission and request.method == 'POST' and request.POST.get('action') == 'update_document':
        document_fields = {
            'aadhar_card': 'Aadhar details',
            'admission_form_doc': 'Admission form',
            'family_id_doc': 'Family ID document',
            'marksheet_10th': '10th marksheet',
            'marksheet_10th_plus': '10th+ marksheet',
        }
        document_field = request.POST.get('document_field')
        upload = request.FILES.get('document_file')

        if document_field in document_fields and upload:
            setattr(admission, document_field, upload)
            admission.save(update_fields=[document_field])
            messages.success(request, f"{document_fields[document_field]} updated successfully.")
            return redirect(f"{profile_base_url}#documents")

        active_profile_tab = 'documents'
        messages.error(request, "Please choose a valid document file.")

    if is_admin_or_center and request.method == 'POST' and request.POST.get('action') == 'change_password':
        active_profile_tab = 'password'
        target_user = admission.user if admission and admission.user else (profile.user if profile else None)
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not target_user:
            messages.error(request, "Student login user is not linked.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters.")
        elif new_password != confirm_password:
            messages.error(request, "New password and confirm password do not match.")
        else:
            target_user.set_password(new_password)
            target_user.save(update_fields=['password'])
            messages.success(request, "Student password updated successfully.")
            return redirect(f"{profile_base_url}#password")

    if is_admin_or_center:
        if target_profile:
            profile_fees_url = f"{profile_base_url}#fees"
            edit_payment_id = request.GET.get('edit_payment') if request.method == 'GET' else None
            if edit_payment_id:
                editing_fee_payment = FeePayment.objects.filter(pk=edit_payment_id, student=target_profile).first()
                if editing_fee_payment:
                    fee_payment_action = 'update_fee_payment'
                    show_fee_payment_form = True

            fee_payment_form = FeePaymentForm(
                instance=editing_fee_payment,
                initial={'student': target_profile.pk},
                user=request.user,
                course_fee=course_fee,
            )

            if request.method == 'POST' and request.POST.get('action') in ['add_fee_payment', 'update_fee_payment']:
                action = request.POST.get('action')
                post_data = request.POST.copy()
                post_data['student'] = str(target_profile.pk)
                if action == 'update_fee_payment':
                    editing_fee_payment = FeePayment.objects.filter(
                        pk=request.POST.get('payment_id'),
                        student=target_profile,
                    ).first()
                    fee_payment_action = 'update_fee_payment'

                fee_payment_form = FeePaymentForm(
                    post_data,
                    instance=editing_fee_payment,
                    user=request.user,
                    course_fee=course_fee,
                )
                show_fee_payment_form = True

                if action == 'update_fee_payment' and not editing_fee_payment:
                    messages.error(request, "Selected fee payment was not found.")
                elif fee_payment_form.is_valid():
                    fee_payment_form.save()
                    messages.success(
                        request,
                        "Fee payment updated successfully." if action == 'update_fee_payment' else "Fee payment added successfully.",
                    )
                    return redirect(profile_fees_url)

                if fee_payment_form.errors:
                    messages.error(request, "Please correct the fee payment fields.")
        elif request.method == 'POST' and request.POST.get('action') in ['add_fee_payment', 'update_fee_payment']:
            messages.error(request, "Student profile is required before adding a fee payment.")
            show_fee_payment_form = True

    if target_profile:
        fee_payments = FeePayment.objects.filter(student=target_profile).order_by('-payment_date', '-id')
        paid_amount = fee_payments.aggregate(total=Sum('amount'))['total'] or 0.00
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
        'fee_payments': fee_payments,
        'certificates': student_certificates,
        'issued_certificates_count': issued_count,
        'eligibility': eligibility,
        'fee_payment_form': fee_payment_form,
        'show_fee_payment_form': show_fee_payment_form,
        'fee_payment_action': fee_payment_action,
        'editing_fee_payment': editing_fee_payment,
        'active_profile_tab': active_profile_tab,
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


@login_required
def student_my_attendance(request):
    if request.user.role != 'student':
        return HttpResponseForbidden("Access Denied: Students only.")

    from apps.attendance.models import Attendance
    from django.core.paginator import Paginator

    admission = StudentAdmission.objects.select_related('course', 'center').filter(user=request.user).first()

    if not admission:
        attendances = Attendance.objects.none()
    else:
        attendances = Attendance.objects.filter(student=admission).select_related('batch', 'marked_by').order_by('-date')

    # Paginate
    paginator = Paginator(attendances, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'student/my_attendance.html', {
        'page_obj': page_obj,
        'admission': admission,
    })

def sync_student_admission_user(admission):
    """
    Creates student user login and links it with StudentAdmission.
    Also creates/updates the StudentProfile.
    """
    from apps.accounts.models import User
    from apps.students.models import StudentProfile
    from apps.batches.models import Batch

    # Find or create Django User for this student admission
    user = None
    if admission.enrollment_no:
        user = User.objects.filter(username=admission.enrollment_no).first()
    if not user and admission.email:
        user = User.objects.filter(email__iexact=admission.email, role='student').first()

    if not user:
        username = admission.enrollment_no if admission.enrollment_no else f"std_{admission.id}"
        email = admission.email if admission.email else f"{username}@example.com"
        user = User.objects.create_user(
            username=username,
            email=email,
            password='student123',
            role='student',
            first_name=admission.student_name
        )
    else:
        if user.role != 'student':
            user.role = 'student'
            user.save()

    # Link admission with the user
    if admission.user != user:
        admission.user = user
        admission.save()

    # Create/update StudentProfile
    profile, created = StudentProfile.objects.get_or_create(user=user)
    profile.full_name = admission.student_name
    profile.email = admission.email if admission.email else f"{user.username}@example.com"
    profile.phone = admission.whatsapp_no
    
    # Try to link to a batch if course and center match
    if not profile.batch and admission.course:
        batch = Batch.objects.filter(course=admission.course, center=admission.center).first()
        if batch:
            profile.batch = batch
            
    if profile.course_fee_at_admission is None and admission.course:
        profile.course_fee_at_admission = admission.course.fees
        
    profile.save()
    return user


@login_required
def student_admission_view(request):
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")

    from django.db import transaction
    from apps.fees.services import deduct_center_wallet_for_student_fee, get_student_payment_amount

    admission_fee = get_student_payment_amount('Admission Fees')
    center_context = request.user.center if request.user.role == 'center' else None

    if request.method == 'POST':
        form = StudentAdmissionForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                admission = form.save(commit=False)
                if request.user.role == 'center':
                    center = request.user.center
                    try:
                        deduct_center_wallet_for_student_fee(center, 'Admission Fees')
                    except ValueError as exc:
                        form.add_error(None, str(exc))
                    else:
                        admission.center = center
                        admission.save()
                        center_context = center
                        sync_student_admission_user(admission)
                        messages.success(request, f"Student Admission processed successfully. ₹{admission_fee:.2f} deducted from wallet.")
                        return redirect('student_admission')
                else:
                    admission.save()
                    sync_student_admission_user(admission)
                    messages.success(request, 'Student Admission processed successfully.')
                    return redirect('student_admission')
    else:
        form = StudentAdmissionForm(user=request.user)
    
    return render(request, 'student/student_admission.html', {
        'form': form,
        'admission_fee': admission_fee,
        'center_wallet_balance': center_context.wallet_balance if center_context else None,
        'center_context': center_context,
    })


# ---------------------------------------------------------------------------
# Student Details — Search & Quick Profile
# ---------------------------------------------------------------------------

@login_required
def student_details_view(request):
    """Search student by enrollment no / name / mobile and display quick profile."""
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    from django.http import JsonResponse
    from django.db.models import Q

    student = None
    admission = None
    error = None

    enrollment = request.GET.get('enrollment', '').strip()
    if enrollment:
        try:
            qs = StudentAdmission.objects.select_related('center', 'course')
            if request.user.role == 'center':
                qs = qs.filter(center=request.user.center)
            admission = qs.get(enrollment_no=enrollment)
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
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    from django.http import JsonResponse
    from django.db.models import Q

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        qs = StudentAdmission.objects.all()
        if request.user.role == 'center':
            qs = qs.filter(center=request.user.center)
        qs = (
            qs.filter(
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
    if request.user.role not in ['admin', 'center', 'superadmin', 'student']:
        return HttpResponseForbidden("Access Denied.")
    
    from django.db.models import Q
    admission = None
    error = None

    if request.user.role == 'student':
        admission = StudentAdmission.objects.select_related('center', 'course').filter(user=request.user).first()
        if not admission:
            error = 'No admission record found for your user.'
    else:
        student_id = request.GET.get('student_id', '').strip()
        if student_id:
            try:
                qs = StudentAdmission.objects.select_related('center', 'course')
                if request.user.role == 'center':
                    qs = qs.filter(center=request.user.center)
                admission = qs.get(pk=student_id)
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
        qs = qs.filter(center=request.user.center)  # Center can only see their own admissions

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
    from django.db import transaction
    from apps.fees.services import deduct_center_wallet_for_student_fee
    
    redirect_url = request.META.get('HTTP_REFERER') or 'student_pending_list'
    
    if request.method == 'POST':
        if request.user.role not in ['admin', 'center']:
            messages.error(request, 'Permission denied.')
            return redirect(redirect_url)
            
        try:
            with transaction.atomic():
                admission = StudentAdmission.objects.select_for_update().get(pk=pk, status__in=['Pending', 'Cancelled'])
                original_status = admission.status
                deducted_amount = 0

                # Center can only approve own students
                if request.user.role == 'center' and admission.center and admission.center != request.user.center:
                    messages.error(request, 'Permission denied.')
                    return redirect(redirect_url)

                if request.user.role == 'center' and original_status == 'Cancelled':
                    deducted_amount = deduct_center_wallet_for_student_fee(request.user.center, 'Re-Admission Fees')

                admission.status = 'Approved'
                admission.approved_by = request.user
                admission.approved_at = timezone.now()
                admission.cancelled_by = None
                admission.cancelled_at = None
                admission.cancel_reason = None
                admission.save()
                sync_student_admission_user(admission)

            if deducted_amount:
                messages.success(request, f'Student Admission Approved Successfully. Rs.{deducted_amount:.2f} deducted from wallet.')
            else:
                messages.success(request, 'Student Admission Approved Successfully.')
            
        except StudentAdmission.DoesNotExist:
            messages.error(request, 'Admission not found or is already Approved.')
        except ValueError as exc:
            messages.error(request, str(exc))

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
            if request.user.role == 'center' and admission.center and admission.center != request.user.center:
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
        qs = qs.filter(center=request.user.center)

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
def create_student_login_password(request, pk):
    """Allow admin/center users to set the login password for an approved student."""
    from apps.accounts.models import User

    if request.user.role not in ['admin', 'center']:
        return redirect('student_dashboard')

    admission = get_object_or_404(
        StudentAdmission.objects.select_related('center', 'course', 'user'),
        pk=pk,
        status='Approved',
    )

    if request.user.role == 'center' and admission.center and admission.center != request.user.center:
        messages.error(request, 'Permission denied.')
        return redirect('student_approved_list')

    user = sync_student_admission_user(admission)
    created_password = None
    form_errors = []

    if request.method == 'POST':
        password = (request.POST.get('password') or '').strip()
        confirm_password = (request.POST.get('confirm_password') or '').strip()
        desired_username = (admission.enrollment_no or '').strip()

        if not password:
            form_errors.append('Password is required.')
        if password and len(password) < 6:
            form_errors.append('Password must be at least 6 characters long.')
        if password != confirm_password:
            form_errors.append('Confirm password must match the password.')
        if not desired_username:
            form_errors.append('Enrollment number is required before creating a student login.')

        if desired_username and user.username != desired_username:
            username_exists = User.all_objects.filter(username__iexact=desired_username).exclude(pk=user.pk).exists()
            if username_exists:
                form_errors.append('This enrollment number is already used by another login account.')

        if not form_errors:
            user.username = desired_username
            user.email = admission.email or user.email
            user.first_name = admission.student_name
            user.role = 'student'
            user.is_active = True
            user.set_password(password)
            user.save(update_fields=['username', 'email', 'first_name', 'role', 'is_active', 'password'])

            if admission.user_id != user.id:
                admission.user = user
                admission.save(update_fields=['user', 'updated_at'])

            created_password = password
            messages.success(request, 'Student password created successfully.')

    return render(request, 'student/create_student_password.html', {
        'admission': admission,
        'login_user': user,
        'created_password': created_password,
        'form_errors': form_errors,
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
        qs = qs.filter(center=request.user.center)

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
            if request.user.role == 'center' and admission.center and admission.center != request.user.center:
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
        if request.user.center:
            selected_center_id = str(request.user.center.id)
            # Filter centers list to only their own center for center role
            centers = centers.filter(id=request.user.center.id)
        else:
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


