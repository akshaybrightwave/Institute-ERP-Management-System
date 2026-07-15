import uuid
from apps.accounts.models import User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from apps.accounts.views import admin_required
from .models import Center
from .forms import CenterCertificateUpdateForm, CenterForm
from .services import create_center_certificate_for_center


@admin_required
def center_list(request):
    form = CenterForm()

    if request.method == 'POST':
        post_data = request.POST.copy()
        if 'phone' not in post_data or not post_data.get('phone'):
            post_data['phone'] = '1234567890'
        form = CenterForm(post_data)
        if form.is_valid():
            with transaction.atomic():
                center = form.save(commit=False)
                if not center.code:
                    center.code = f"CTR-{uuid.uuid4().hex[:6].upper()}"
                center.save()
                create_center_certificate_for_center(center, created_by=request.user)
            messages.success(request, 'Center created successfully.')
            return redirect('center_list')

    query = request.GET.get('q', '').strip()
    qs = Center.objects.all().order_by('-id')
    if query:
        qs = qs.filter(name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'centers/center_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@admin_required
def pending_centers(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        center_id = request.POST.get('center_id')
        if action == 'approve' and center_id:
            center = get_object_or_404(Center, id=center_id)
            if hasattr(center, 'center_user') and center.center_user:
                center.center_user.is_active = True
                center.center_user.save()
                messages.success(request, f"{center.name} has been approved.")
            else:
                messages.error(request, "Error: User account for this center not found.")
            return redirect('pending_centers')

    query = request.GET.get('q', '').strip()
    name_filter = request.GET.get('name', '').strip()
    state_filter = request.GET.get('state', '').strip()
    city_filter = request.GET.get('city', '').strip()
    
    # Assuming pending means the associated User is not active
    qs = Center.objects.filter(center_user__is_active=False).order_by('-id')
    
    if query:
        qs = qs.filter(name__icontains=query)
    if name_filter:
        qs = qs.filter(name__icontains=name_filter)
    if state_filter:
        qs = qs.filter(state__icontains=state_filter)
    if city_filter:
        qs = qs.filter(district__icontains=city_filter)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'centers/pending_centers.html', {
        'page_obj': page_obj,
        'query': query,
    })


@admin_required
def center_info_list(request):
    query = request.GET.get('q', '').strip()
    
    # Base queryset for all active centers (not soft-deleted)
    qs = Center.objects.filter(center_user__is_active=True).prefetch_related('course_assignments').order_by('-id')
    
    if query:
        qs = qs.filter(name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'centers/center_info_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


from django.views.decorators.http import require_http_methods
from decimal import Decimal, InvalidOperation


@admin_required
@require_http_methods(["GET", "POST"])
def load_wallet(request, pk):
    """
    GET  → return center name + current wallet balance as JSON (for modal population)
    POST → add the submitted amount to the center's wallet_balance
    """
    center = get_object_or_404(Center, pk=pk)

    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'AJAX only'}, status=400)

    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'center_name': center.name,
            'wallet_balance': str(center.wallet_balance),
        })

    # POST — validate and credit the wallet
    amount_raw = request.POST.get('amount', '').strip()
    description = request.POST.get('description', '').strip()

    if not amount_raw:
        return JsonResponse({'success': False, 'errors': {'amount': ['Amount is required.']}})

    try:
        amount = Decimal(amount_raw)
    except InvalidOperation:
        return JsonResponse({'success': False, 'errors': {'amount': ['Enter a valid numeric amount.']}})

    if amount <= 0:
        return JsonResponse({'success': False, 'errors': {'amount': ['Amount must be greater than zero.']}})

    center.wallet_balance += amount
    center.save(update_fields=['wallet_balance'])

    return JsonResponse({
        'success': True,
        'new_balance': str(center.wallet_balance),
        'message': f'₹{amount} added to {center.name} wallet successfully.',
    })


@admin_required
def center_create(request):
    if request.method == 'POST':
        form = CenterForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                # Generate a unique code
                center = form.save(commit=False)
                if not center.code:
                    center.code = f"CTR-{uuid.uuid4().hex[:6].upper()}"
                center.save()

                create_center_certificate_for_center(center, created_by=request.user)
                
                # Create user for the center
                email = form.cleaned_data.get('email')
                password = form.cleaned_data.get('password')
                
                # Use email as username if not provided
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    role='center',
                    center=center
                )
                user.is_active = False
                user.save()
            
            messages.success(request, 'Center created successfully.')
            return redirect('center_list')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CenterForm()
    return render(request, 'centers/center_form.html', {'form': form, 'action': 'Create'})


from django.utils import timezone

@admin_required
def center_update(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        form = CenterForm(request.POST, request.FILES, instance=center)
        if form.is_valid():
            center = form.save()
            
            # Sync user model details
            password = form.cleaned_data.get('password')
            email = form.cleaned_data.get('email')
            if hasattr(center, 'center_user') and center.center_user:
                user_updated = False
                if email and center.center_user.email != email:
                    center.center_user.username = email
                    center.center_user.email = email
                    user_updated = True
                if password:
                    center.center_user.set_password(password)
                    user_updated = True
                if user_updated:
                    center.center_user.save()
            
            # Update Profile Status
            status_val = request.POST.get('is_deleted')
            if status_val is not None:
                is_deleted = status_val == 'true' or status_val == 'True' or status_val == '1'
                if center.is_deleted != is_deleted:
                    center.is_deleted = is_deleted
                    if is_deleted:
                        center.deleted_at = timezone.now()
                    else:
                        center.deleted_at = None
                    center.save(update_fields=['is_deleted', 'deleted_at'])
            
            messages.success(request, 'Center updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('center_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'id': center.pk,
                'owner_name': center.owner_name,
                'name': center.name,
                'code': center.code,
                'head_qualification': center.head_qualification,
                'prefix_roll_no': center.prefix_roll_no,
                'owner_dob': center.owner_dob.strftime('%Y-%m-%d') if center.owner_dob else '',
                'pan_number': center.pan_number,
                'aadhar_number': center.aadhar_number,
                'address': center.address,
                'pincode': center.pincode,
                'state': center.state,
                'district': center.district,
                'staff_count': center.staff_count,
                'classrooms_count': center.classrooms_count,
                'computers_count': center.computers_count,
                'space_sqft': center.space_sqft,
                'whatsapp_number': center.whatsapp_number,
                'phone': center.phone,
                'email': center.email,
                'has_reception': 'True' if center.has_reception else 'False',
                'has_staff_room': 'True' if center.has_staff_room else 'False',
                'has_water_supply': 'True' if center.has_water_supply else 'False',
                'has_toilet': 'True' if center.has_toilet else 'False',
                'valid_upto': center.valid_upto.strftime('%Y-%m-%d') if center.valid_upto else '',
                'is_deleted': center.is_deleted,
            })
        form = CenterForm(instance=center)
    return render(request, 'centers/center_form.html', {'form': form, 'action': 'Update', 'center': center})


@admin_required
def center_delete(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        center.delete()
        messages.success(request, 'Center deleted successfully.')
        return redirect('center_list')
    return render(request, 'centers/center_confirm_delete.html', {'center': center})


@login_required
def center_dashboard(request):
    if request.user.role != 'center':
        return redirect('login')
        
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

        qs = StudentAdmission.objects.filter(center=request.user.center, created_at__year=year)
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
    
    from apps.batches.models import Batch
    from apps.students.models import StudentProfile
    from apps.students.models import StudentAdmission
    from apps.certificates.models import Certificate
    from apps.attendance.models import Attendance
    from apps.fees.models import FeePayment
    from apps.exams.models import Exam, StudentExamAttempt
    from apps.admit_card.models import AdmitCard
    from apps.results.models import Result
    from django.db.models import Count, DecimalField, Q, Sum, Value
    from django.db.models.functions import Coalesce
    from django.urls import reverse
    from decimal import Decimal
    from django.utils import timezone
    
    center = request.user.center
    
    if not center:
        context = {
            'center': None,
            'center_status': 'Inactive',
            'center_certificate': None,
            'wallet_balance': Decimal('0.00'),
            'dashboard_cards': [],
            'total_assigned_courses': 0,
            'total_course_categories': 0,
            'total_students': 0,
            'active_students': 0,
            'passout_students': 0,
            'total_admissions': 0,
            'approved_admissions': 0,
            'pending_admissions': 0,
            'cancelled_admissions': 0,
            'total_exams': 0,
            'total_admit_cards': 0,
            'total_results': 0,
            'total_id_cards': 0,
            'total_certificates': 0,
            'total_fee_collection': Decimal('0.00'),
            'attendance_present': 0,
            'attendance_absent': 0,
            'attendance_total': 0,
            'attendance_pct': 0.0,
            'total_attempts': 0,
            'recent_students': [],
            'recent_batches': [],
            'upcoming_exams': [],
        }
        return render(request, 'centers/center_dashboard.html', context)

    from apps.centers.models import CenterCertificate, CenterCourseAssignment

    today = timezone.localdate()
    center_status = 'Inactive' if center.is_deleted or (center.valid_upto and center.valid_upto < today) else 'Active'
    center_certificate = CenterCertificate.objects.filter(center=center).only(
        'id', 'certificate_number', 'valid_upto', 'certificate_status'
    ).first()

    assigned_courses = CenterCourseAssignment.objects.filter(
        center=center,
        is_active=True,
    ).select_related('course', 'course__category')
    assigned_course_ids = list(assigned_courses.values_list('course_id', flat=True))

    batches = Batch.objects.filter(center=center).select_related('course', 'teacher')
    students = StudentProfile.objects.filter(batch__center=center).select_related('user', 'batch', 'batch__course')
    admissions = StudentAdmission.objects.filter(center=center).select_related('course', 'center')

    admission_counts = admissions.aggregate(
        total=Count('id'),
        approved=Count('id', filter=Q(status='Approved')),
        pending=Count('id', filter=Q(status='Pending')),
        cancelled=Count('id', filter=Q(status='Cancelled')),
    )
    total_admissions = admission_counts['total'] or 0
    approved_admissions = admission_counts['approved'] or 0
    pending_admissions = admission_counts['pending'] or 0
    cancelled_admissions = admission_counts['cancelled'] or 0

    active_students = students.filter(user__is_deleted=False).count()
    total_students = students.count()
    passout_students = Certificate.objects.filter(center=center).count()
    total_course_categories = assigned_courses.exclude(course__category__isnull=True).values('course__category_id').distinct().count()
    total_assigned_courses = len(set(assigned_course_ids))
    total_admit_cards = AdmitCard.objects.filter(student__center=center).count()
    total_results = Result.objects.filter(student__center=center).count()
    total_id_cards = approved_admissions
    total_fee_collection = FeePayment.objects.filter(student__batch__center=center).aggregate(
        total=Coalesce(Sum('amount'), Value(Decimal('0.00')), output_field=DecimalField(max_digits=12, decimal_places=2))
    )['total']
    total_exams = Exam.objects.filter(
        Q(center=center) | Q(batches__center=center) | Q(course_id__in=assigned_course_ids)
    ).distinct().count()
    total_certificates = passout_students

    attendance_stats = Attendance.objects.filter(batch__center=center).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent'))
    )
    attendance_total = attendance_stats['total'] or 0
    attendance_present = attendance_stats['present'] or 0
    attendance_absent = attendance_stats['absent'] or 0
    attendance_pct = round((attendance_present / attendance_total * 100), 1) if attendance_total else 0.0

    total_attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch__center=center).count()
    recent_students = students.order_by('-user__date_joined')[:5]
    recent_batches = batches.order_by('-id')[:5]
    upcoming_exams = Exam.objects.filter(
        Q(center=center) | Q(batches__center=center) | Q(course_id__in=assigned_course_ids),
        date__gte=today,
    ).distinct().prefetch_related('batches').order_by('date')[:5]

    dashboard_cards = [
        {'label': 'Active Students', 'value': active_students, 'icon': 'bi-mortarboard-fill', 'class': 'bg-g-purple', 'url': reverse('student_list_by_center'), 'action': 'View List'},
        {'label': 'Passout Students', 'value': passout_students, 'icon': 'bi-award-fill', 'class': 'bg-g-cyan', 'url': reverse('passout_student_list'), 'action': 'View List'},
        {'label': 'Course Categories', 'value': total_course_categories, 'icon': 'bi-tags-fill', 'class': 'bg-g-green', 'url': reverse('course_list'), 'action': 'View Courses'},
        {'label': 'Assigned Courses', 'value': total_assigned_courses, 'icon': 'bi-journal-bookmark-fill', 'class': 'bg-g-pink', 'url': reverse('course_list'), 'action': 'View Courses'},
        {'label': 'Admissions', 'value': total_admissions, 'icon': 'bi-person-plus-fill', 'class': 'bg-g-blue', 'url': reverse('student_list_by_center'), 'action': 'View List'},
        {'label': 'Approved Admissions', 'value': approved_admissions, 'icon': 'bi-person-check-fill', 'class': 'bg-g-orange', 'url': reverse('student_approved_list'), 'action': 'View List'},
        {'label': 'Pending Admissions', 'value': pending_admissions, 'icon': 'bi-hourglass-split', 'class': 'bg-g-red', 'url': reverse('student_pending_list'), 'action': 'View List'},
        {'label': 'Cancelled Admissions', 'value': cancelled_admissions, 'icon': 'bi-person-x-fill', 'class': 'bg-g-violet', 'url': reverse('student_cancelled_list'), 'action': 'View List'},
        {'label': 'Admit Cards', 'value': total_admit_cards, 'icon': 'bi-card-text', 'class': 'bg-g-crimson', 'url': reverse('admit_card_list'), 'action': 'View List'},
        {'label': 'Results', 'value': total_results, 'icon': 'bi-file-earmark-bar-graph-fill', 'class': 'bg-g-amber', 'url': reverse('result_list'), 'action': 'View List'},
        {'label': 'ID Cards', 'value': total_id_cards, 'icon': 'bi-person-badge-fill', 'class': 'bg-g-olive', 'url': reverse('student_id_card'), 'action': 'View Cards'},
        {'label': 'Fee Collection', 'value': f"Rs.{total_fee_collection}", 'icon': 'bi-cash-stack', 'class': 'bg-g-navy', 'url': reverse('fees_list'), 'action': 'View Fees', 'small': True},
    ]

    context = {
        'center': center,
        'center_status': center_status,
        'center_certificate': center_certificate,
        'wallet_balance': center.wallet_balance or Decimal('0.00'),
        'dashboard_cards': dashboard_cards,
        'total_assigned_courses': total_assigned_courses,
        'total_course_categories': total_course_categories,
        'total_students': total_students,
        'active_students': active_students,
        'passout_students': passout_students,
        'total_admissions': total_admissions,
        'approved_admissions': approved_admissions,
        'pending_admissions': pending_admissions,
        'cancelled_admissions': cancelled_admissions,
        'total_exams': total_exams,
        'total_admit_cards': total_admit_cards,
        'total_results': total_results,
        'total_id_cards': total_id_cards,
        'total_certificates': total_certificates,
        'total_fee_collection': total_fee_collection,
        'attendance_present': attendance_present,
        'attendance_absent': attendance_absent,
        'attendance_total': attendance_total,
        'attendance_pct': attendance_pct,
        'total_attempts': total_attempts,
        'recent_students': recent_students,
        'recent_batches': recent_batches,
        'upcoming_exams': upcoming_exams,
    }
    return render(request, 'centers/center_dashboard.html', context)


from apps.courses.models import Course
from apps.centers.models import CenterCourseAssignment
import json

@admin_required
def assign_courses(request):
    centers = Center.objects.all().order_by('name')
    courses = Course.objects.all().order_by('name')
    return render(request, 'centers/assign_courses.html', {
        'centers': centers,
        'courses': courses
    })

@admin_required
def api_center_courses(request, center_id):
    center = get_object_or_404(Center, pk=center_id)
    # Use CenterCourseAssignment as the source of truth (Phase 1+)
    assignments = CenterCourseAssignment.objects.filter(
        center=center
    ).select_related('course').order_by('-assigned_date')

    assigned_ids = [a.course_id for a in assignments]
    courses_data = []
    for assignment in assignments:
        c = assignment.course
        courses_data.append({
            'id': c.id,
            'name': c.name,
            'duration': c.duration,
            'fees': str(c.fees) if c.fees else '0',
            'assigned_date': assignment.assigned_date.strftime('%d %b %Y') if assignment.assigned_date else 'N/A',
            'is_active': assignment.is_active
        })
    center_data = {
        'id': center.id,
        'name': center.name,
        'code': center.code,
        'owner_name': center.owner_name or 'N/A',
        'status': 'Inactive' if center.is_deleted else 'Active',
        'total_assigned': len(assignments),
        'logo_url': center.logo_doc.url if center.logo_doc else None
    }
    return JsonResponse({
        'center': center_data,
        'assigned_ids': assigned_ids,
        'assigned_courses': courses_data
    })

@admin_required
def api_assign_course_toggle(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)
    try:
        data = json.loads(request.body)
        center_id = data.get('center_id')
        course_id = data.get('course_id')
        action = data.get('action')  # 'assign' or 'remove'

        center = Center.objects.get(pk=center_id)
        course = Course.objects.get(pk=course_id)

        if action == 'assign':
            # Create assignment in CenterCourseAssignment (Phase 1+)
            assignment, created = CenterCourseAssignment.objects.get_or_create(
                center=center,
                course=course,
                defaults={
                    'is_active': True,
                    'assigned_by': request.user if request.user.is_authenticated else None
                }
            )
            if not created:
                # Already exists — make sure it's active
                assignment.is_active = True
                assignment.save(update_fields=['is_active'])

            msg = 'Course assigned successfully.'
        else:
            # Remove from CenterCourseAssignment
            CenterCourseAssignment.objects.filter(center=center, course=course).delete()

            msg = 'Course removed successfully.'

        return JsonResponse({'success': True, 'message': msg})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


@admin_required
def center_profile(request, pk):
    center = get_object_or_404(
        Center.all_objects.select_related('center_user')
        .prefetch_related('admissions', 'course_assignments'),
        pk=pk
    )
    is_admin = getattr(request.user, 'role', None) == 'admin'
    total_students = center.admissions.count()
    total_courses = center.course_assignments.count()
    registration_date = center.center_user.date_joined if hasattr(center, 'center_user') and center.center_user else None

    from decimal import Decimal, InvalidOperation
    from apps.fees.models import StudentPaymentSetting
    from apps.fees.services import sync_student_payment_settings

    sync_student_payment_settings()
    admission_fee_setting = StudentPaymentSetting.objects.filter(title__iexact='Admission Fees').first()

    if request.method == 'POST' and request.POST.get('action') == 'update_admission_fee_setting':
        if not is_admin:
            return HttpResponseForbidden("Access Denied: Only admins can update fee settings.")

        amount_raw = request.POST.get('admission_fee_amount', '').strip()
        try:
            amount = Decimal(amount_raw)
        except InvalidOperation:
            amount = None

        if amount is None or amount < Decimal('0.00'):
            messages.error(request, "Enter a valid admission fee amount.")
        else:
            admission_fee_setting.amount = amount
            admission_fee_setting.is_visible = request.POST.get('admission_fee_enabled') == 'on'
            admission_fee_setting.save(update_fields=['amount', 'is_visible', 'updated_at'])
            messages.success(request, "Admission fee setting updated successfully.")
            return redirect(f"{request.path}#fees")

    return render(request, 'centers/center_profile.html', {
        'center': center,
        'total_students': total_students,
        'total_courses': total_courses,
        'registration_date': registration_date,
        'admission_fee_setting': admission_fee_setting,
        'can_update_fee_setting': is_admin,
    })


@admin_required
def deleted_centers(request):
    if request.method == 'POST' and request.POST.get('action') == 'hard_delete':
        center_id = request.POST.get('center_id')
        if center_id:
            center = get_object_or_404(Center.all_objects, pk=center_id)
            center.hard_delete()
            messages.success(request, f"Center '{center.name}' has been permanently deleted.")
            return redirect('deleted_centers')

    query = request.GET.get('q', '').strip()
    
    # Base queryset for all soft-deleted centers
    qs = Center.all_objects.filter(is_deleted=True).prefetch_related('course_assignments').order_by('-deleted_at')
    
    if query:
        qs = qs.filter(name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'centers/deleted_centers.html', {
        'page_obj': page_obj,
        'query': query,
    })


@admin_required
def restore_center(request, pk):
    center = get_object_or_404(Center.all_objects, pk=pk)
    if request.method == 'POST':
        center.restore()
        if hasattr(center, 'center_user') and center.center_user:
            center.center_user.restore()
        messages.success(request, 'Center restored successfully.')
        return redirect('deleted_centers')
    return redirect('deleted_centers')


import csv
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseForbidden
from .models import CenterCertificate

def _handle_center_cert_list_and_csv(request, is_center):
    qs = CenterCertificate.objects.select_related('center', 'created_by').all()
    if is_center:
        qs = qs.filter(center=request.user.center)

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(center__name__icontains=query) |
            Q(center__code__icontains=query) |
            Q(certificate_number__icontains=query)
        )
    qs = qs.order_by('-id')

    # Handle CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="center_certificates.csv"'
        writer = csv.writer(response)
        writer.writerow(['Institute Code', 'Institute Name', 'Owner Name', 'Issue Date', 'Valid Upto', 'Status'])
        for cert in qs:
            writer.writerow([
                cert.center.code if cert.center else '',
                cert.center.name if cert.center else '',
                cert.center.owner_name if cert.center else '',
                cert.issue_date,
                cert.valid_upto,
                cert.certificate_status
            ])
        return response

    return qs, query

@login_required
def center_certificate_list(request):
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    qs, query = _handle_center_cert_list_and_csv(request, is_center)
    if isinstance(qs, HttpResponse):
        return qs

    show_entries = request.GET.get('show', '10')
    paginator = Paginator(qs, int(show_entries))
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'centers/center_certificate_list.html', {
        'page_obj': page_obj,
        'query': query,
        'is_admin': is_admin,
        'is_center': is_center,
        'show_entries': show_entries,
    })

@login_required
def center_certificate_create(request):
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    messages.info(
        request,
        'Center certificates are generated automatically when a center is created.'
    )
    return redirect('center_certificate_list')

@login_required
def center_certificate_detail(request, pk):
    cert = get_object_or_404(CenterCertificate.objects.select_related('center'), pk=pk)
    
    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied: This certificate belongs to another center.")
    if request.user.role not in ['admin', 'superadmin', 'SUPER_ADMIN', 'center']:
        return HttpResponseForbidden("Access Denied")

    return render(request, 'centers/center_certificate_detail.html', {
        'cert': cert
    })

@login_required
def center_certificate_update(request, pk):
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    cert = get_object_or_404(
        CenterCertificate.objects.select_related('center'),
        pk=pk
    )
    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied: This certificate belongs to another center.")

    if request.method == 'POST':
        form = CenterCertificateUpdateForm(request.POST, instance=cert)
        if form.is_valid():
            form.save()
            messages.success(request, f"Certificate {cert.certificate_number} updated successfully.")
            return redirect('center_certificate_list')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = CenterCertificateUpdateForm(instance=cert)

    return render(request, 'centers/center_certificate_edit.html', {
        'form': form,
        'cert': cert,
    })

@login_required
def center_certificate_delete(request, pk):
    if request.user.role not in ['admin', 'center', 'superadmin']:
        return HttpResponseForbidden("Access Denied.")
    cert = get_object_or_404(CenterCertificate.objects.select_related('center'), pk=pk)
    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied")

    if request.method == 'POST':
        cert.delete()
        messages.success(request, f"Certificate {cert.certificate_number} deleted successfully.")
    
    return redirect(request.META.get('HTTP_REFERER', 'center_certificate_create'))
