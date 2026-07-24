from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import (
    AdminSignupForm,
    CenterEditForm,
    CenterSignupForm,
    FeedbackForm,
    InvestigatorEditForm,
    InvestigatorSignupForm,
    StudentEditForm,
    StudentSignupForm,
    SuperAdminUserCreationForm,
    TeacherEditForm,
    TeacherSignupForm,
)
from django.contrib.auth.decorators import login_required
from django.contrib import messages  
from django.http import HttpResponseForbidden
from functools import wraps

from django.core.paginator import Paginator
from django.db.models import Q
from apps.exams.models import Exam
from apps.teachers.models import TeacherProfile
from .auth_logging import log_auth_activity
from .models import AuthActivityLog, User, Feedback

# Create your views here.

REGISTRATION_DISABLED_MESSAGE = 'Public registration is disabled. Please contact the Super Admin for credentials.'

ROLE_DASHBOARD_URLS = {
    'SUPER_ADMIN': 'management_super_admin_dashboard',
    'superadmin': 'management_super_admin_dashboard',
    'admin': 'admin_dashboard',
    'center': 'center_dashboard',
    'teacher': 'teacher_dashboard',
    'student': 'student_dashboard',
    'hr': 'hr:dashboard',
    'telecaller': 'management_dashboard',
    'counselor': 'counselor_dashboard',
    'investigator': 'investigator_dashboard',
}


def registration_disabled(request):
    log_auth_activity(
        'REGISTRATION_BLOCKED',
        request=request,
        username=request.POST.get('username', ''),
        details='Public registration endpoint was accessed.',
    )
    return HttpResponseForbidden(REGISTRATION_DISABLED_MESSAGE)


def is_super_admin_user(user):
    return user.is_authenticated and user.role == 'SUPER_ADMIN'


def super_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if is_super_admin_user(request.user):
            return view_func(request, *args, **kwargs)
        log_auth_activity(
            'UNAUTHORIZED_ACCESS',
            request=request,
            user=request.user if request.user.is_authenticated else None,
            details='Non-Super Admin attempted to access the Super Admin panel.',
        )
        return HttpResponseForbidden("Access Denied: Super Admins only.")
    return wrapper


def role_dashboard_name(user):
    return ROLE_DASHBOARD_URLS.get(getattr(user, 'role', None), 'login')

def redirect_to_role_dashboard(user):
    return redirect(role_dashboard_name(user))

def home(request):
    exams = Exam.objects.order_by('-date', '-id')  # fallback by id if date same
    paginator = Paginator(exams, 3)  # 3 exams per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/home.html', {'page_obj': page_obj})

def signup_admin(request):
    return registration_disabled(request)



def signup_teacher(request):
    return registration_disabled(request)

# from django.db import transaction
# # def signup_teacher(request):
#     if request.method == 'POST':
#         form = TeacherSignupForm(request.POST)
#         if form.is_valid():
#             try:
#                 with transaction.atomic():
#                     user = form.save()

#                     # Explicit TeacherProfile creation
#                     profile = TeacherProfile.objects.create(
#                         user=user,
#                         full_name=user.username,  # Ensure valid data
#                         email=user.email
#                     )

#                     print(f"TeacherProfile created for {user.username}")

#                 messages.success(request, 'Teacher account created successfully. Please log in.')
#                 return redirect('login')

#             except Exception as e:
#                 print('Error creating TeacherProfile:', e)
#                 messages.error(request, 'Something went wrong. Please try again.')

#     else:
#         form = TeacherSignupForm()

#     return render(request, 'accounts/signup_teacher.html', {'form': form})







def signup_student(request):
    return registration_disabled(request)



def user_login(request):
    if request.user.is_authenticated:
        return redirect_to_role_dashboard(request.user)

    if request.method == 'POST':
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Please enter both username and password')
            return redirect('login')

        auth_username = username
        lookup_user = User.all_objects.filter(email__iexact=username).first()
        if lookup_user:
            auth_username = lookup_user.username

        user = authenticate(request, username=auth_username, password=password)
        if user:
            log_auth_activity('LOGIN_SUCCESS', request=request, user=user, username=username)
            login(request, user)
            return redirect_to_role_dashboard(user)
        else:
            log_auth_activity(
                'LOGIN_FAILED',
                request=request,
                username=username,
                details='Invalid credentials or inactive/nonexistent account.',
            )
            messages.error(request, 'Invalid credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required
def dashboard_redirect(request):
    return redirect_to_role_dashboard(request.user)


@login_required
def user_logout(request):
    log_auth_activity('LOGOUT', request=request, user=request.user, username=request.user.username)
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')



#to restrict views to User Admins

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('admin', 'superadmin'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Admins only.")
    return wrapper



# Admin Dashboard and CRUD Views 

from django.shortcuts import get_object_or_404


@login_required
@super_admin_required
def superadmin_dashboard(request):
    users = User.all_objects.exclude(role='SUPER_ADMIN')
    context = {
        'total_users': users.count(),
        'admin_count': users.filter(role='admin').count(),
        'hr_count': users.filter(role='hr').count(),
        'telecaller_count': users.filter(role='telecaller').count(),
        'counselor_count': users.filter(role='counselor').count(),
        'active_users': users.filter(is_active=True, is_deleted=False).count(),
        'recent_users': users.order_by('-date_joined')[:8],
        'recent_logs': AuthActivityLog.objects.select_related('user').order_by('-created_at')[:10],
    }
    return render(request, 'accounts/superadmin_dashboard.html', context)


@login_required
@super_admin_required
def superadmin_user_add(request):
    if request.method == 'POST':
        form = SuperAdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_auth_activity(
                'USER_CREATED',
                request=request,
                user=request.user,
                username=user.username,
                details=f"Super Admin created {user.get_role_display()} credentials for {user.username}.",
            )
            messages.success(request, f"{user.get_role_display()} credentials created successfully.")
            return redirect('superadmin_dashboard')
    else:
        form = SuperAdminUserCreationForm()
    return render(request, 'accounts/superadmin_user_add.html', {'form': form})


@login_required
@super_admin_required
def superadmin_activity_logs(request):
    logs = AuthActivityLog.objects.select_related('user').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    event = request.GET.get('event', '').strip()

    if query:
        logs = logs.filter(
            Q(username__icontains=query) |
            Q(details__icontains=query) |
            Q(path__icontains=query) |
            Q(ip_address__icontains=query)
        )
    if event:
        logs = logs.filter(event_type=event)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'accounts/superadmin_activity_logs.html', {
        'page_obj': page_obj,
        'query': query,
        'event': event,
        'event_choices': AuthActivityLog.EVENT_CHOICES,
    })

@admin_required
def admin_dashboard(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' and request.GET.get('action') == 'admission_trend':
        from django.http import JsonResponse
        from django.db.models.functions import ExtractMonth, Cast
        from django.db.models import Count, DateField
        from apps.students.models import StudentAdmission
        import datetime
        
        year_str = request.GET.get('year')
        try:
            year = int(year_str)
        except (TypeError, ValueError):
            year = datetime.date.today().year

        qs = StudentAdmission.objects.filter(created_at__year=year)
        trend = qs.annotate(
            created_date=Cast('created_at', DateField())
        ).annotate(
            month=ExtractMonth('created_date')
        ).values('month').annotate(count=Count('id')).order_by('month')
        
        data = [0] * 12
        for item in trend:
            if item['month']:
                month_index = item['month'] - 1
                data[month_index] = item['count']
                
        return JsonResponse({'data': data})

    from apps.centers.models import Center
    from apps.courses.models import Course
    from apps.batches.models import Batch
    from apps.attendance.models import Attendance
    from apps.students.models import StudentProfile, StudentAdmission
    from apps.fees.models import FeePayment
    from apps.categories.models import Category
    from apps.admit_card.models import AdmitCard
    from apps.results.models import Result
    from apps.exams.models import Exam, StudentExamAttempt
    from apps.certificates.models import Certificate
    from django.db.models import Sum, F, Count, Q
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    import datetime

    today = datetime.date.today()

    # ── Fee metrics (2 queries → combined) ────────────────────────────────────
    fee_agg = FeePayment.objects.aggregate(total=Coalesce(Sum('amount'), Decimal('0.00')))
    total_fee_collection = fee_agg['total']

    course_fee_agg = StudentProfile.objects.aggregate(
        total=Coalesce(Sum('course_fee_at_admission'), Decimal('0.00'))
    )
    total_course_fees = course_fee_agg['total']
    total_pending_fees = total_course_fees - total_fee_collection

    students_with_pending_fees = StudentProfile.objects.annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'))
    ).filter(
        batch__course__isnull=False,
        paid_amount__lt=F('course_fee_at_admission')
    ).count()

    # ── Certificate & Exam metrics ─────────────────────────────────────────────
    total_certificates = Certificate.objects.count()
    issued_certificates_count = total_certificates

    # ── Eligible students: replaced Python loop with DB annotation ─────────────
    # Students with ≥75% attendance AND fees fully paid
    # Keep payment and attendance aggregates separate to avoid a slow multi-join.
    paid_map = {
        p['student_id']: p['total'] or Decimal('0.00')
        for p in FeePayment.objects.values('student_id').annotate(total=Sum('amount'))
    }
    attendance_by_user = Attendance.objects.exclude(student__user__isnull=True).values(
        'student__user_id'
    ).annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
    )
    att_map = {
        a['student__user_id']: (a['total'], a['present'])
        for a in attendance_by_user
    }

    eligible_students_count = 0
    eligible_students = StudentProfile.objects.filter(
        batch__isnull=False,
        batch__course__isnull=False,
    ).select_related('batch__course', 'user')
    for student in eligible_students:
        paid = paid_map.get(student.id, Decimal('0.00'))
        course_fee = Decimal(str(student.course_fee_at_admission or '0.00'))
        total_att, present_att = att_map.get(student.user_id, (0, 0))
        attendance_pct = (present_att / total_att) * 100 if total_att else 0.0
        if paid >= course_fee and attendance_pct >= 75.0:
            eligible_students_count += 1

    # ── Dashboard Analytics (combined where possible) ─────────────────────────
    user_counts = User.objects.aggregate(
        active_students=Count('id', filter=Q(role='student', is_active=True, is_deleted=False)),
        active_teachers=Count('id', filter=Q(role='teacher', is_active=True, is_deleted=False)),
    )
    active_students = StudentAdmission.objects.filter(status='Approved').count()
    active_teachers = user_counts['active_teachers']

    active_batches = Batch.objects.filter(start_date__lte=today, end_date__gte=today).count()

    # Attendance rate: 2 queries → 1 aggregate
    att_agg = Attendance.objects.aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
    )
    total_att_count = att_agg['total']
    present_att_count = att_agg['present']
    attendance_rate = round((present_att_count / total_att_count * 100), 1) if total_att_count > 0 else 0.0

    fee_collection_rate = round((float(total_fee_collection) / float(total_course_fees) * 100), 1) if total_course_fees > 0 else 0.0

    # Exam pass rate: 2 queries → 1 aggregate
    exam_agg = StudentExamAttempt.objects.filter(is_completed=True).aggregate(
        total=Count('id'),
        passed=Count('id', filter=Q(score__gte=F('exam__pass_percentage'))),
    )
    total_attempts = exam_agg['total']
    passed_attempts = exam_agg['passed']
    exam_pass_rate = round((passed_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    # ── KPI metrics ────────────────────────────────────────────────────────────
    total_course_categories = Category.objects.count()

    admission_counts = StudentAdmission.objects.aggregate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='Approved')),
        pending=Count('id', filter=Q(status='Pending')),
        cancelled=Count('id', filter=Q(status='Cancelled')),
    )
    total_admissions = admission_counts['total'] or 0
    approved_admissions = admission_counts['approved'] or 0
    pending_admissions = admission_counts['pending'] or 0
    cancelled_admissions = admission_counts['cancelled'] or 0

    total_admit_cards = AdmitCard.objects.count()
    total_results = Result.objects.count()
    total_id_cards = approved_admissions

    center_agg = Center.objects.aggregate(
        pending=Count('id', filter=Q(center_user__is_active=False)),
        approved=Count('id', filter=Q(center_user__is_active=True)),
    )
    total_pending_centers = center_agg['pending']
    total_approved_centers = center_agg['approved']

    # Batch/exam/course aggregate counts
    exam_counts = Exam.objects.aggregate(
        total=Count('id'),
        published=Count('id', filter=Q(is_published=True)),
        batch_assigned=Count('id', filter=Q(batches__isnull=False), distinct=True),
    )

    # Total students/teachers (admin side) - combine into one query
    user_total_agg = User.objects.aggregate(
        total_students=Count('id', filter=Q(role='student', is_deleted=False)),
        total_teachers=Count('id', filter=Q(role='teacher', is_deleted=False)),
    )

    context = {
        'total_students': user_total_agg['total_students'],
        'total_teachers': user_total_agg['total_teachers'],
        'total_exams': exam_counts['total'],
        'active_exams': exam_counts['published'],
        'batch_assigned_exams': exam_counts['batch_assigned'],
        'unread_feedback_count': Feedback.objects.filter(is_read=False).count(),
        'total_centers': Center.objects.count(),
        'total_courses': Course.objects.count(),
        'total_batches': Batch.objects.count(),
        'total_attendance_records': total_att_count,
        'total_fee_collection': total_fee_collection,
        'total_pending_fees': total_pending_fees,
        'students_with_pending_fees': students_with_pending_fees,
        'total_certificates': total_certificates,
        'issued_certificates_count': issued_certificates_count,
        'revoked_certificates_count': 0,
        'eligible_students_count': eligible_students_count,
        'active_students': active_students,
        'active_teachers': active_teachers,
        'active_batches': active_batches,
        'attendance_rate': attendance_rate,
        'fee_collection_rate': fee_collection_rate,
        'exam_pass_rate': exam_pass_rate,
        'certificate_issuance_count': issued_certificates_count,
        # KPI variables
        'total_course_categories': total_course_categories,
        'total_admissions': total_admissions,
        'approved_admissions': approved_admissions,
        'pending_admissions': pending_admissions,
        'cancelled_admissions': cancelled_admissions,
        'total_admit_cards': total_admit_cards,
        'total_results': total_results,
        'total_id_cards': total_id_cards,
        'total_pending_centers': total_pending_centers,
        'total_approved_centers': total_approved_centers,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@login_required
def user_list(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    if request.user.role == 'center':
        if not request.user.center:
            users = User.objects.none()
        else:
            users = User.objects.filter(
                Q(role='student', studentprofile__batch__center=request.user.center) |
                Q(role='student', studentprofile__batch__isnull=True) |
                Q(role='teacher', teacherprofile__batch__center=request.user.center) |
                Q(role='teacher', teacherprofile__batch__isnull=True)
            ).filter(is_deleted=False).distinct()
    else:
        users = User.objects.filter(is_deleted=False).exclude(role='admin')

    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    selected_batch_id = request.GET.get('batch', '').strip()

    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
    if role in ('student', 'teacher', 'center', 'investigator'):
        users = users.filter(role=role)
    if selected_batch_id:
        users = users.filter(studentprofile__batch_id=selected_batch_id)

    from apps.batches.models import Batch
    if request.user.role == 'center':
        batches = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True) if request.user.center else Batch.objects.none()
    else:
        batches = Batch.objects.all()

    return render(request, 'accounts/user_list.html', {
        'users': users,
        'query': query,
        'role': role,
        'batches': batches,
        'selected_batch_id': selected_batch_id,
    })


@login_required
def user_add(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    role = request.GET.get('role')
    if request.user.role == 'center' and role not in ('student', 'teacher'):
        return HttpResponseForbidden("Access Denied: You cannot create Admin/Center accounts.")

    if role == 'student':
        form_class = StudentSignupForm
    elif role == 'teacher':
        form_class = TeacherSignupForm
    elif role == 'center':
        form_class = CenterSignupForm
    elif role == 'investigator' and request.user.role == 'admin':
        form_class = InvestigatorSignupForm
    else:
        return HttpResponseForbidden("Invalid role.")

    if request.method == 'POST':
        if role == 'student':
            form = form_class(request.POST, is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True) if request.user.center else Batch.objects.none()
        else:
            form = form_class(request.POST)

        if form.is_valid():
            if role == 'student' and request.user.role == 'center':
                batch = form.cleaned_data.get('batch')
                if batch and (not request.user.center or batch.center != request.user.center):
                    return HttpResponseForbidden("Access Denied: You cannot assign students to other center batches.")
            form.save()
            return redirect('user_list')
    else:
        if role == 'student':
            form = form_class(is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True) if request.user.center else Batch.objects.none()
        else:
            form = form_class()

    return render(request, 'accounts/user_add.html', {'form': form, 'role': role})


@login_required
def user_edit(request, user_id):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    user = get_object_or_404(User, id=user_id, is_deleted=False)

    if request.user.role == 'center':
        if user.role not in ('student', 'teacher'):
            return HttpResponseForbidden("Access Denied: You cannot edit Admin/Center accounts.")
        if user.role == 'student':
            from apps.students.models import StudentProfile
            try:
                profile = user.studentprofile
                if profile.batch and profile.batch.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: This student is in a batch belonging to another center.")
            except StudentProfile.DoesNotExist:
                pass
        elif user.role == 'teacher':
            try:
                profile = user.teacherprofile
                if profile.batch_set.exclude(course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
                    return HttpResponseForbidden("Access Denied: This teacher is assigned to another center's batch.")
            except TeacherProfile.DoesNotExist:
                pass

    if user.role == 'student':
        form_class = StudentEditForm
    elif user.role == 'teacher':
        form_class = TeacherEditForm
    elif user.role == 'center':
        form_class = CenterEditForm
    elif user.role == 'investigator' and request.user.role == 'admin':
        form_class = InvestigatorEditForm
    else:
        return HttpResponseForbidden("Invalid user type.")

    if request.method == 'POST':
        if user.role == 'student':
            form = form_class(request.POST, instance=user, is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True) if request.user.center else Batch.objects.none()
        else:
            form = form_class(request.POST, instance=user)

        if form.is_valid():
            if user.role == 'student' and request.user.role == 'center':
                batch = form.cleaned_data.get('batch')
                if batch and (not request.user.center or batch.center != request.user.center):
                    return HttpResponseForbidden("Access Denied: You cannot assign students to other center batches.")
            form.save()
            if user.role == 'student':
                messages.success(request, "Student updated successfully.")
            elif user.role == 'teacher':
                messages.success(request, "Teacher updated successfully.")
            elif user.role == 'center':
                messages.success(request, "Center updated successfully.")
            return redirect('user_list')
    else:
        if user.role == 'student':
            form = form_class(instance=user, is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True) if request.user.center else Batch.objects.none()
        else:
            form = form_class(instance=user)

    return render(request, 'accounts/user_edit.html', {'form': form, 'edited_user': user})


@login_required
def user_delete(request, user_id):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    user = get_object_or_404(User, id=user_id, is_deleted=False)
    if user.role == 'admin':
        return HttpResponseForbidden("Cannot delete admin user.")

    if request.user.role == 'center':
        if user.role not in ('student', 'teacher'):
            return HttpResponseForbidden("Access Denied: You cannot delete Admin/Center accounts.")
        if user.role == 'student':
            from apps.students.models import StudentProfile
            try:
                profile = user.studentprofile
                if profile.batch and profile.batch.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: This student belongs to another center.")
            except StudentProfile.DoesNotExist:
                pass
        elif user.role == 'teacher':
            try:
                profile = user.teacherprofile
                if profile.batch_set.exclude(course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
                    return HttpResponseForbidden("Access Denied: This teacher belongs to another center.")
            except TeacherProfile.DoesNotExist:
                pass

    for profile_attr in ('studentprofile', 'teacherprofile'):
        profile = getattr(user, profile_attr, None)
        if profile:
            profile.delete()
    user.delete()
    messages.success(request, f"User {user.username} deleted successfully.")
    return redirect('user_list')



#contact 
# def contact_view(request):
#     if request.method == 'POST':
#         form = FeedbackForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Thank you for your feedback!')
#             return redirect('contact')  
#     else:
#         form = FeedbackForm()
#     return render(request, 'accounts/contact.html', {'form': form})

def contact_view(request):
    if request.method=='POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your feedback')
            return redirect('contact')
    else:
        form= FeedbackForm()
    return render(request,'accounts/contact.html',{'form':form})


# Admin Feedback Inbox

@admin_required
def feedback_list(request):
    feedbacks = Feedback.objects.all().order_by('-submitted_at')

    status = request.GET.get('status', '').strip()
    if status == 'unread':
        feedbacks = feedbacks.filter(is_read=False)

    paginator = Paginator(feedbacks, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/feedback_list.html', {
        'page_obj': page_obj,
        'status': status,
        'unread_count': Feedback.objects.filter(is_read=False).count(),
    })


@admin_required
def feedback_detail(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if not feedback.is_read:
        feedback.is_read = True
        feedback.save()
    return render(request, 'accounts/feedback_detail.html', {'feedback': feedback})


@admin_required
def feedback_delete(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if request.method == 'POST':
        feedback.delete()
        messages.success(request, 'Feedback message deleted.')
        return redirect('feedback_list')
    return render(request, 'accounts/feedback_delete.html', {'feedback': feedback})




