from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import (
    AdminSignupForm,
    CenterEditForm,
    CenterSignupForm,
    FeedbackForm,
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
    'SUPER_ADMIN': 'superadmin_dashboard',
    'superadmin': 'management_super_admin_dashboard',
    'admin': 'admin_dashboard',
    'center': 'center_dashboard',
    'teacher': 'teacher_dashboard',
    'student': 'student_dashboard',
    'hr': 'hr:dashboard',
    'telecaller': 'management_dashboard',
    'counselor': 'counselor_dashboard',
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
    from apps.centers.models import Center
    from apps.courses.models import Course
    from apps.batches.models import Batch
    from apps.attendance.models import Attendance
    from apps.students.models import StudentProfile
    from apps.fees.models import FeePayment
    from django.db.models import Sum, F
    from django.db.models.functions import Coalesce
    from decimal import Decimal

    # Fee metrics
    total_fee_collection = FeePayment.objects.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_course_fees = StudentProfile.objects.aggregate(total=Sum('batch__course__fees'))['total'] or Decimal('0.00')
    total_pending_fees = Decimal(str(total_course_fees)) - Decimal(str(total_fee_collection))
    
    students_with_pending_fees = StudentProfile.objects.annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'))
    ).filter(
        batch__course__isnull=False,
        paid_amount__lt=F('batch__course__fees')
    ).count()

    # Certificate & Exam metrics
    from apps.certificates.models import Certificate
    from apps.exams.models import StudentExamAttempt
    from django.db.models import Count, Q
    
    total_certificates = Certificate.objects.count()
    issued_certificates_count = Certificate.objects.filter(status='issued').count()
    revoked_certificates_count = Certificate.objects.filter(status='revoked').count()

    # Calculate count of eligible students
    paid_map = {p['student_id']: p['total'] or Decimal('0.00') for p in FeePayment.objects.values('student_id').annotate(total=Sum('amount'))}
    att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}

    eligible_students_count = 0
    for student in StudentProfile.objects.filter(batch__isnull=False).select_related('batch', 'batch__course'):
        paid = paid_map.get(student.id, Decimal('0.00'))
        course_fee = Decimal(str(student.batch.course.fees)) if (student.batch and student.batch.course) else Decimal('0.00')
        fee_eligible = paid >= course_fee
        
        total_att, present_att = att_map.get(student.id, (0, 0))
        attendance_pct = (present_att / total_att) * 100 if total_att > 0 else 0.0
        attendance_eligible = attendance_pct >= 75.0
        
        if fee_eligible and attendance_eligible:
            eligible_students_count += 1

    # Dashboard Analytics (ERP Phase 8)
    import datetime
    today = datetime.date.today()
    active_students = User.objects.filter(role='student', is_active=True, is_deleted=False).count()
    active_teachers = User.objects.filter(role='teacher', is_active=True, is_deleted=False).count()
    active_batches = Batch.objects.filter(start_date__lte=today, end_date__gte=today).count()
    
    total_att_count = Attendance.objects.count()
    present_att_count = Attendance.objects.filter(status='present').count()
    attendance_rate = round((present_att_count / total_att_count * 100), 1) if total_att_count > 0 else 0.0
    
    fee_collection_rate = round((total_fee_collection / total_course_fees * 100), 1) if total_course_fees > 0 else 0.0
    
    total_attempts = StudentExamAttempt.objects.filter(is_completed=True).count()
    passed_attempts = StudentExamAttempt.objects.filter(is_completed=True, score__gte=F('exam__pass_percentage')).count()
    exam_pass_rate = round((passed_attempts / total_attempts * 100), 1) if total_attempts > 0 else 0.0

    context = {
        'total_students': User.objects.filter(role='student', is_deleted=False).count(),
        'total_teachers': User.objects.filter(role='teacher', is_deleted=False).count(),
        'total_exams': Exam.objects.count(),
        'active_exams': Exam.objects.filter(is_published=True).count(),
        'batch_assigned_exams': Exam.objects.filter(batches__isnull=False).distinct().count(),
        'unread_feedback_count': Feedback.objects.filter(is_read=False).count(),
        'total_centers': Center.objects.count(),
        'total_courses': Course.objects.count(),
        'total_batches': Batch.objects.count(),
        'total_attendance_records': Attendance.objects.count(),
        'total_fee_collection': total_fee_collection,
        'total_pending_fees': total_pending_fees,
        'students_with_pending_fees': students_with_pending_fees,
        'total_certificates': total_certificates,
        'issued_certificates_count': issued_certificates_count,
        'revoked_certificates_count': revoked_certificates_count,
        'eligible_students_count': eligible_students_count,
        'active_students': active_students,
        'active_teachers': active_teachers,
        'active_batches': active_batches,
        'attendance_rate': attendance_rate,
        'fee_collection_rate': fee_collection_rate,
        'exam_pass_rate': exam_pass_rate,
        'certificate_issuance_count': issued_certificates_count,
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
                Q(role='student', studentprofile__batch__course__center=request.user.center) |
                Q(role='student', studentprofile__batch__isnull=True) |
                Q(role='teacher', teacherprofile__batch__course__center=request.user.center) |
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
    if role in ('student', 'teacher', 'center'):
        users = users.filter(role=role)
    if selected_batch_id:
        users = users.filter(studentprofile__batch_id=selected_batch_id)

    from apps.batches.models import Batch
    if request.user.role == 'center':
        batches = Batch.objects.filter(course__center=request.user.center) if request.user.center else Batch.objects.none()
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
    else:
        return HttpResponseForbidden("Invalid role.")

    if request.method == 'POST':
        if role == 'student':
            form = form_class(request.POST, is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__center=request.user.center) if request.user.center else Batch.objects.none()
        else:
            form = form_class(request.POST)

        if form.is_valid():
            if role == 'student' and request.user.role == 'center':
                batch = form.cleaned_data.get('batch')
                if batch and (not request.user.center or batch.course.center != request.user.center):
                    return HttpResponseForbidden("Access Denied: You cannot assign students to other center batches.")
            form.save()
            return redirect('user_list')
    else:
        if role == 'student':
            form = form_class(is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__center=request.user.center) if request.user.center else Batch.objects.none()
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
                if profile.batch and profile.batch.course.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: This student is in a batch belonging to another center.")
            except StudentProfile.DoesNotExist:
                pass
        elif user.role == 'teacher':
            try:
                profile = user.teacherprofile
                if profile.batch_set.exclude(course__center=request.user.center).exists():
                    return HttpResponseForbidden("Access Denied: This teacher is assigned to another center's batch.")
            except TeacherProfile.DoesNotExist:
                pass

    if user.role == 'student':
        form_class = StudentEditForm
    elif user.role == 'teacher':
        form_class = TeacherEditForm
    elif user.role == 'center':
        form_class = CenterEditForm
    else:
        return HttpResponseForbidden("Invalid user type.")

    if request.method == 'POST':
        if user.role == 'student':
            form = form_class(request.POST, instance=user, is_admin=True)
            if request.user.role == 'center':
                from apps.batches.models import Batch
                form.fields['batch'].queryset = Batch.objects.filter(course__center=request.user.center) if request.user.center else Batch.objects.none()
        else:
            form = form_class(request.POST, instance=user)

        if form.is_valid():
            if user.role == 'student' and request.user.role == 'center':
                batch = form.cleaned_data.get('batch')
                if batch and (not request.user.center or batch.course.center != request.user.center):
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
                form.fields['batch'].queryset = Batch.objects.filter(course__center=request.user.center) if request.user.center else Batch.objects.none()
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
                if profile.batch and profile.batch.course.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: This student belongs to another center.")
            except StudentProfile.DoesNotExist:
                pass
        elif user.role == 'teacher':
            try:
                profile = user.teacherprofile
                if profile.batch_set.exclude(course__center=request.user.center).exists():
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




