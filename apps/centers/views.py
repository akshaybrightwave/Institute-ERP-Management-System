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
    qs = Center.objects.prefetch_related('course_assignments').order_by('-id')
    
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
                User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    role='center',
                    center=center
                )
            
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
    
    from apps.courses.models import Course
    from apps.batches.models import Batch
    from apps.accounts.models import User
    from apps.students.models import StudentProfile
    from apps.certificates.models import Certificate
    from apps.attendance.models import Attendance
    from apps.fees.models import FeePayment
    from apps.exams.models import Exam, StudentExamAttempt
    from django.db.models import Sum, Count, Q, F
    from django.db.models.functions import Coalesce
    from decimal import Decimal
    from django.utils import timezone
    import datetime
    
    center = request.user.center
    
    if not center:
        context = {
            'total_courses': 0,
            'total_batches': 0,
            'total_teachers': 0,
            'total_students': 0,
            'total_exams': 0,
            'total_certificates': 0,
            'attendance_present': 0,
            'attendance_absent': 0,
            'attendance_total': 0,
            'attendance_pct': 0.0,
            'total_fees_collected': Decimal('0.00'),
            'total_pending_fees': Decimal('0.00'),
            'paid_students_count': 0,
            'pending_students_count': 0,
            'certs_issued_count': 0,
            'certs_revoked_count': 0,
            'eligible_students_count': 0,
            'active_exams_count': 0,
            'completed_exams_count': 0,
            'total_attempts': 0,
            'recent_students': [],
            'recent_batches': [],
            'upcoming_exams': [],
            'performance_attendance_rate': 0.0,
            'performance_fee_collection_rate': 0.0,
            'performance_exam_participation_rate': 0.0,
            'performance_cert_eligibility_rate': 0.0,
            # Phase 10.9 defaults
            'mon_total_exams': 0,
            'mon_published_exams': 0,
            'mon_active_exams': 0,
            'mon_total_attempts': 0,
            'mon_students_appeared': 0,
            'mon_avg_score': 0.0,
            'mon_pass_pct': 0.0,
            'mon_fail_pct': 0.0,
            'mon_top_performers': [],
            'mon_low_performers': [],
            'mon_batch_perf': [],
            # Phase 10.10 defaults
            'att_present_today': 0,
            'att_absent_today': 0,
            'att_monthly_pct': 0.0,
            'att_students_below_75': 0,
        }
        return render(request, 'centers/center_dashboard.html', context)

    # 1. Overview Metrics (Feature 1)
    total_courses = Course.objects.filter(center=center).count()
    total_batches = Batch.objects.filter(course__assignments__center=center, course__assignments__is_active=True).count()
    total_teachers = User.objects.filter(role='teacher', is_deleted=False, teacherprofile__batch__center=center).distinct().count()
    total_students = User.objects.filter(role='student', is_deleted=False, studentprofile__batch__center=center).distinct().count()
    total_exams = Exam.objects.filter(batches__course__assignments__center=center, course__assignments__is_active=True).distinct().count()
    total_certificates = Certificate.objects.filter(course__assignments__center=center, course__assignments__is_active=True).count()

    # 2. Attendance Summary (Feature 2)
    att_stats = Attendance.objects.filter(batch__center=center).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent'))
    )
    attendance_total = att_stats['total']
    attendance_present = att_stats['present']
    attendance_absent = att_stats['absent']
    attendance_pct = (attendance_present / attendance_total * 100) if attendance_total > 0 else 0.0

    # 2.5 Attendance Monitoring Metrics (Phase 10.10)
    today = datetime.date.today()
    att_present_today = Attendance.objects.filter(
        batch__center=center, 
        date=today, 
        status='present'
    ).count()
    att_absent_today = Attendance.objects.filter(
        batch__center=center, 
        date=today, 
        status='absent'
    ).count()
    
    start_of_month = today.replace(day=1)
    monthly_stats = Attendance.objects.filter(
        batch__center=center, 
        date__gte=start_of_month, 
        date__lte=today
    ).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present'))
    )
    monthly_total = monthly_stats['total']
    monthly_present = monthly_stats['present']
    att_monthly_pct = round((monthly_present / monthly_total * 100), 1) if monthly_total > 0 else 0.0
    
    # Students Below 75% Overall Attendance (having at least 1 attendance log)
    center_students = StudentProfile.objects.filter(batch__center=center)
    low_attendance_students = center_students.annotate(
        total_att=Count('attendances'),
        present_att=Count('attendances', filter=Q(attendances__status='present'))
    )
    att_students_below_75 = low_attendance_students.filter(
        total_att__gt=0,
        present_att__lt=F('total_att') * 0.75
    ).count()

    # 3. Fees Summary (Feature 3)
    total_fees_collected = FeePayment.objects.filter(student__batch__center=center).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_course_fees = StudentProfile.objects.filter(batch__center=center).aggregate(total=Sum('batch__course__fees'))['total'] or Decimal('0.00')
    total_pending_fees = Decimal(str(total_course_fees)) - Decimal(str(total_fees_collected))
    
    # Calculate Paid / Pending Students using annotated single query
    students_stats = StudentProfile.objects.filter(batch__center=center).annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'))
    ).select_related('batch', 'batch__course')
    
    paid_students_count = 0
    pending_students_count = 0
    for student in students_stats:
        course_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
        if student.paid_amount >= course_fee:
            paid_students_count += 1
        else:
            pending_students_count += 1

    # 4. Certificate Summary (Feature 4)
    certs_issued_count = Certificate.objects.filter(course__assignments__center=center, course__assignments__is_active=True, status='issued').count()
    certs_revoked_count = Certificate.objects.filter(course__assignments__center=center, course__assignments__is_active=True, status='revoked').count()
    
    # Eligible Students Calculation
    att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.filter(batch__center=center).values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}

    eligible_students_count = 0
    for student in students_stats:
        course_fee = Decimal(str(student.batch.course.fees)) if (student.batch and student.batch.course) else Decimal('0.00')
        fee_eligible = student.paid_amount >= course_fee
        
        total_att, present_att = att_map.get(student.id, (0, 0))
        student_att_pct = (present_att / total_att) * 100 if total_att > 0 else 0.0
        attendance_eligible = student_att_pct >= 75.0
        
        if fee_eligible and attendance_eligible:
            eligible_students_count += 1

    # 5. Exam Summary (Feature 5)
    active_exams_count = Exam.objects.filter(batches__course__assignments__center=center, course__assignments__is_active=True, is_published=True).distinct().count()
    completed_exams_count = Exam.objects.filter(
        batches__course__assignments__center=center, course__assignments__is_active=True, 
        attempts__student__studentprofile__batch__center=center,
        attempts__is_completed=True
    ).distinct().count()
    total_attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch__center=center).count()

    # Phase 10.9: Center Exam Operations & Monitoring calculations
    center_exams = Exam.objects.filter(batches__course__assignments__center=center, course__assignments__is_active=True).distinct()
    mon_total_exams = center_exams.count()
    mon_published_exams = center_exams.filter(is_published=True).count()
    mon_active_exams = center_exams.filter(is_published=True).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())).count()
    
    center_attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch__center=center)
    mon_total_attempts = center_attempts.count()
    mon_students_appeared = center_attempts.values('student').distinct().count()
    
    completed_center_attempts = center_attempts.filter(is_completed=True).select_related('exam', 'student__studentprofile__batch')
    total_completed = completed_center_attempts.count()
    
    total_pct = 0.0
    pass_count = 0
    fail_count = 0
    student_performance = {}
    
    for att in completed_center_attempts:
        max_marks = att.exam.total_marks
        pct = (att.score / max_marks * 100) if max_marks > 0 else 0.0
        total_pct += pct
        
        pass_threshold = (att.exam.pass_percentage / 100.0) * max_marks
        if att.score >= pass_threshold:
            pass_count += 1
        else:
            fail_count += 1
            
        student_id = att.student_id
        student_name = att.student.studentprofile.full_name
        batch_name = att.student.studentprofile.batch.name if att.student.studentprofile.batch else 'N/A'
        
        if student_id not in student_performance:
            student_performance[student_id] = {
                'name': student_name,
                'batch': batch_name,
                'total_pct': 0.0,
                'count': 0
            }
        student_performance[student_id]['total_pct'] += pct
        student_performance[student_id]['count'] += 1
        
    mon_avg_score = (total_pct / total_completed) if total_completed > 0 else 0.0
    mon_pass_pct = (pass_count / total_completed * 100) if total_completed > 0 else 0.0
    mon_fail_pct = (fail_count / total_completed * 100) if total_completed > 0 else 0.0
    
    student_averages = []
    for s_id, s_data in student_performance.items():
        avg_pct = s_data['total_pct'] / s_data['count']
        student_averages.append({
            'name': s_data['name'],
            'batch': s_data['batch'],
            'avg_pct': round(avg_pct, 1)
        })
        
    mon_top_performers = sorted(student_averages, key=lambda x: x['avg_pct'], reverse=True)[:5]
    mon_low_performers = sorted(student_averages, key=lambda x: x['avg_pct'])[:5]
    
    center_batches = Batch.objects.filter(course__assignments__center=center, course__assignments__is_active=True).prefetch_related('exams')
    mon_batch_perf = []
    for batch in center_batches:
        students_count = StudentProfile.objects.filter(batch=batch).count()
        exam_count = batch.exams.count()
        
        b_attempts = StudentExamAttempt.objects.filter(
            student__studentprofile__batch=batch,
            is_completed=True
        ).select_related('exam')
        b_attempt_count = b_attempts.count()
        
        b_total_pct = 0.0
        b_pass_count = 0
        b_fail_count = 0
        for att in b_attempts:
            max_marks = att.exam.total_marks
            pct = (att.score / max_marks * 100) if max_marks > 0 else 0.0
            b_total_pct += pct
            
            pass_threshold = (att.exam.pass_percentage / 100.0) * max_marks
            if att.score >= pass_threshold:
                b_pass_count += 1
            else:
                b_fail_count += 1
                
        b_avg_score = (b_total_pct / b_attempt_count) if b_attempt_count > 0 else 0.0
        b_pass_pct = (b_pass_count / b_attempt_count * 100) if b_attempt_count > 0 else 0.0
        b_fail_pct = (b_fail_count / b_attempt_count * 100) if b_attempt_count > 0 else 0.0
        
        mon_batch_perf.append({
            'name': batch.name,
            'students_count': students_count,
            'exam_count': exam_count,
            'attempt_count': b_attempt_count,
            'avg_score': round(b_avg_score, 1),
            'pass_pct': round(b_pass_pct, 1),
            'fail_pct': round(b_fail_pct, 1),
        })

    # 6. Recent Students (Feature 6)
    recent_students = StudentProfile.objects.filter(
        batch__center=center
    ).select_related('batch', 'user').order_by('-user__date_joined')[:5]

    # 7. Recent Batches (Feature 7)
    recent_batches = Batch.objects.filter(
        course__assignments__center=center, course__assignments__is_active=True
    ).select_related('course', 'teacher').order_by('-id')[:5]

    # 8. Upcoming Exams (Feature 8)
    today = datetime.date.today()
    upcoming_exams = Exam.objects.filter(
        batches__course__assignments__center=center, course__assignments__is_active=True,
        date__gte=today
    ).distinct().prefetch_related('batches').order_by('date')[:5]

    # 9. Performance Snapshot Rates (Feature 10)
    attendance_rate = attendance_pct
    fee_collection_rate = (float(total_fees_collected) / float(total_course_fees) * 100) if total_course_fees > 0 else 0.0
    
    # Exam Participation Rate
    student_exams = StudentProfile.objects.filter(
        batch__center=center,
        batch__isnull=False
    ).annotate(
        exam_count=Count('batch__exams')
    ).aggregate(
        total_potential=Sum('exam_count')
    )
    total_potential_attempts = student_exams['total_potential'] or 0
    actual_attempts = StudentExamAttempt.objects.filter(
        student__studentprofile__batch__center=center,
        is_completed=True
    ).count()
    exam_participation_rate = (actual_attempts / total_potential_attempts * 100) if total_potential_attempts > 0 else 0.0
    
    # Certificate Eligibility Rate
    total_students_enrolled = StudentProfile.objects.filter(batch__center=center).count()
    cert_eligibility_rate = (eligible_students_count / total_students_enrolled * 100) if total_students_enrolled > 0 else 0.0

    context = {
        'total_courses': total_courses,
        'total_batches': total_batches,
        'total_teachers': total_teachers,
        'total_students': total_students,
        'total_exams': total_exams,
        'total_certificates': total_certificates,
        'attendance_present': attendance_present,
        'attendance_absent': attendance_absent,
        'attendance_total': attendance_total,
        'attendance_pct': round(attendance_pct, 1),
        'total_fees_collected': total_fees_collected,
        'total_pending_fees': total_pending_fees,
        'paid_students_count': paid_students_count,
        'pending_students_count': pending_students_count,
        'certs_issued_count': certs_issued_count,
        'certs_revoked_count': certs_revoked_count,
        'eligible_students_count': eligible_students_count,
        'active_exams_count': active_exams_count,
        'completed_exams_count': completed_exams_count,
        'total_attempts': total_attempts,
        'recent_students': recent_students,
        'recent_batches': recent_batches,
        'upcoming_exams': upcoming_exams,
        'performance_attendance_rate': round(attendance_rate, 1),
        'performance_fee_collection_rate': round(fee_collection_rate, 1),
        'performance_exam_participation_rate': round(exam_participation_rate, 1),
        'performance_cert_eligibility_rate': round(cert_eligibility_rate, 1),
        # Phase 10.9 variables
        'mon_total_exams': mon_total_exams,
        'mon_published_exams': mon_published_exams,
        'mon_active_exams': mon_active_exams,
        'mon_total_attempts': mon_total_attempts,
        'mon_students_appeared': mon_students_appeared,
        'mon_avg_score': round(mon_avg_score, 1),
        'mon_pass_pct': round(mon_pass_pct, 1),
        'mon_fail_pct': round(mon_fail_pct, 1),
        'mon_top_performers': mon_top_performers,
        'mon_low_performers': mon_low_performers,
        'mon_batch_perf': mon_batch_perf,
        # Phase 10.10 variables
        'att_present_today': att_present_today,
        'att_absent_today': att_absent_today,
        'att_monthly_pct': att_monthly_pct,
        'att_students_below_75': att_students_below_75,
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
    total_students = center.admissions.count()
    total_courses = center.course_assignments.count()
    registration_date = center.center_user.date_joined if hasattr(center, 'center_user') and center.center_user else None

    return render(request, 'centers/center_profile.html', {
        'center': center,
        'total_students': total_students,
        'total_courses': total_courses,
        'registration_date': registration_date,
    })


@admin_required
def deleted_centers(request):
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

@admin_required
def center_certificate_list(request):
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

@admin_required
def center_certificate_create(request):
    messages.info(
        request,
        'Center certificates are generated automatically when a center is created.'
    )
    return redirect('center_certificate_list')

@admin_required
def center_certificate_detail(request, pk):
    cert = get_object_or_404(CenterCertificate.objects.select_related('center'), pk=pk)
    
    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied: This certificate belongs to another center.")

    return render(request, 'centers/center_certificate_detail.html', {
        'cert': cert
    })

@admin_required
def center_certificate_update(request, pk):
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

@admin_required
def center_certificate_delete(request, pk):
    cert = get_object_or_404(CenterCertificate.objects.select_related('center'), pk=pk)
    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied")

    if request.method == 'POST':
        cert.delete()
        messages.success(request, f"Certificate {cert.certificate_number} deleted successfully.")
    
    return redirect(request.META.get('HTTP_REFERER', 'center_certificate_create'))
