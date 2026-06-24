from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from apps.accounts.views import admin_required
from .models import Center
from .forms import CenterForm


@admin_required
def center_list(request):
    centers = Center.objects.all()
    return render(request, 'centers/center_list.html', {'centers': centers})


@admin_required
def center_create(request):
    if request.method == 'POST':
        form = CenterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Center created successfully.')
            return redirect('center_list')
    else:
        form = CenterForm()
    return render(request, 'centers/center_form.html', {'form': form, 'action': 'Create'})


@admin_required
def center_update(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        form = CenterForm(request.POST, instance=center)
        if form.is_valid():
            form.save()
            messages.success(request, 'Center updated successfully.')
            return redirect('center_list')
    else:
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
    total_batches = Batch.objects.filter(course__center=center).count()
    total_teachers = User.objects.filter(role='teacher', is_deleted=False, teacherprofile__batch__course__center=center).distinct().count()
    total_students = User.objects.filter(role='student', is_deleted=False, studentprofile__batch__course__center=center).distinct().count()
    total_exams = Exam.objects.filter(batches__course__center=center).distinct().count()
    total_certificates = Certificate.objects.filter(course__center=center).count()

    # 2. Attendance Summary (Feature 2)
    att_stats = Attendance.objects.filter(batch__course__center=center).aggregate(
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
        batch__course__center=center, 
        date=today, 
        status='present'
    ).count()
    att_absent_today = Attendance.objects.filter(
        batch__course__center=center, 
        date=today, 
        status='absent'
    ).count()
    
    start_of_month = today.replace(day=1)
    monthly_stats = Attendance.objects.filter(
        batch__course__center=center, 
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
    center_students = StudentProfile.objects.filter(batch__course__center=center)
    low_attendance_students = center_students.annotate(
        total_att=Count('attendances'),
        present_att=Count('attendances', filter=Q(attendances__status='present'))
    )
    att_students_below_75 = low_attendance_students.filter(
        total_att__gt=0,
        present_att__lt=F('total_att') * 0.75
    ).count()

    # 3. Fees Summary (Feature 3)
    total_fees_collected = FeePayment.objects.filter(student__batch__course__center=center).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    total_course_fees = StudentProfile.objects.filter(batch__course__center=center).aggregate(total=Sum('batch__course__fees'))['total'] or Decimal('0.00')
    total_pending_fees = Decimal(str(total_course_fees)) - Decimal(str(total_fees_collected))
    
    # Calculate Paid / Pending Students using annotated single query
    students_stats = StudentProfile.objects.filter(batch__course__center=center).annotate(
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
    certs_issued_count = Certificate.objects.filter(course__center=center, status='issued').count()
    certs_revoked_count = Certificate.objects.filter(course__center=center, status='revoked').count()
    
    # Eligible Students Calculation
    att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.filter(batch__course__center=center).values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}

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
    active_exams_count = Exam.objects.filter(batches__course__center=center, is_published=True).distinct().count()
    completed_exams_count = Exam.objects.filter(
        batches__course__center=center, 
        attempts__student__studentprofile__batch__course__center=center,
        attempts__is_completed=True
    ).distinct().count()
    total_attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch__course__center=center).count()

    # Phase 10.9: Center Exam Operations & Monitoring calculations
    center_exams = Exam.objects.filter(batches__course__center=center).distinct()
    mon_total_exams = center_exams.count()
    mon_published_exams = center_exams.filter(is_published=True).count()
    mon_active_exams = center_exams.filter(is_published=True).filter(Q(end_date__isnull=True) | Q(end_date__gte=timezone.now())).count()
    
    center_attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch__course__center=center)
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
    
    center_batches = Batch.objects.filter(course__center=center).prefetch_related('exams')
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
        batch__course__center=center
    ).select_related('batch', 'user').order_by('-user__date_joined')[:5]

    # 7. Recent Batches (Feature 7)
    recent_batches = Batch.objects.filter(
        course__center=center
    ).select_related('course', 'teacher').order_by('-id')[:5]

    # 8. Upcoming Exams (Feature 8)
    today = datetime.date.today()
    upcoming_exams = Exam.objects.filter(
        batches__course__center=center,
        date__gte=today
    ).distinct().prefetch_related('batches').order_by('date')[:5]

    # 9. Performance Snapshot Rates (Feature 10)
    attendance_rate = attendance_pct
    fee_collection_rate = (float(total_fees_collected) / float(total_course_fees) * 100) if total_course_fees > 0 else 0.0
    
    # Exam Participation Rate
    student_exams = StudentProfile.objects.filter(
        batch__course__center=center,
        batch__isnull=False
    ).annotate(
        exam_count=Count('batch__exams')
    ).aggregate(
        total_potential=Sum('exam_count')
    )
    total_potential_attempts = student_exams['total_potential'] or 0
    actual_attempts = StudentExamAttempt.objects.filter(
        student__studentprofile__batch__course__center=center,
        is_completed=True
    ).count()
    exam_participation_rate = (actual_attempts / total_potential_attempts * 100) if total_potential_attempts > 0 else 0.0
    
    # Certificate Eligibility Rate
    total_students_enrolled = StudentProfile.objects.filter(batch__course__center=center).count()
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

