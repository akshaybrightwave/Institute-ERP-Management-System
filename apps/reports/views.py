import datetime
import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.db.models import Q, Sum, Count, Avg, F, Max, Min
from django.db.models.functions import Coalesce
from decimal import Decimal

from apps.accounts.models import User
from apps.centers.models import Center
from apps.courses.models import Course
from apps.batches.models import Batch
from apps.students.models import StudentProfile
from apps.teachers.models import TeacherProfile
from apps.attendance.models import Attendance
from apps.fees.models import FeePayment
from apps.exams.models import Exam, StudentExamAttempt
from apps.certificates.models import Certificate


def get_teacher_profile(user):
    try:
        return user.teacherprofile
    except TeacherProfile.DoesNotExist:
        return None


@login_required
def reports_dashboard(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied: Admins, Teachers, or Center users only.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        total_students = StudentProfile.objects.filter(batch__teacher=teacher_profile).count()
        total_teachers = 1
        total_batches = Batch.objects.filter(teacher=teacher_profile).count()
        total_courses = Course.objects.filter(batch__teacher=teacher_profile).distinct().count()
        total_centers = Center.objects.filter(course__batch__teacher=teacher_profile).distinct().count()
        total_exams = Exam.objects.filter(batches__teacher=teacher_profile).distinct().count()
        total_certificates = Certificate.objects.filter(batch__teacher=teacher_profile).count()
        total_attendance_records = Attendance.objects.filter(student__batch__teacher=teacher_profile).count()
    elif is_center:
        center = request.user.center
        if not center:
            total_students = 0
            total_teachers = 0
            total_batches = 0
            total_courses = 0
            total_centers = 0
            total_exams = 0
            total_certificates = 0
            total_attendance_records = 0
        else:
            total_students = StudentProfile.objects.filter(batch__course__center=center).count()
            total_teachers = User.objects.filter(role='teacher', is_deleted=False, teacherprofile__batch__course__center=center).distinct().count()
            total_batches = Batch.objects.filter(course__center=center).count()
            total_courses = Course.objects.filter(center=center).count()
            total_centers = 1
            total_exams = Exam.objects.filter(batches__course__center=center).distinct().count()
            total_certificates = Certificate.objects.filter(course__center=center).count()
            total_attendance_records = Attendance.objects.filter(batch__course__center=center).count()
    else:
        total_students = User.objects.filter(role='student', is_deleted=False).count()
        total_teachers = User.objects.filter(role='teacher', is_deleted=False).count()
        total_batches = Batch.objects.count()
        total_courses = Course.objects.count()
        total_centers = Center.objects.count()
        total_exams = Exam.objects.count()
        total_certificates = Certificate.objects.count()
        total_attendance_records = Attendance.objects.count()

    context = {
        'total_students': total_students,
        'total_teachers': total_teachers,
        'total_batches': total_batches,
        'total_courses': total_courses,
        'total_centers': total_centers,
        'total_exams': total_exams,
        'total_certificates': total_certificates,
        'total_attendance_records': total_attendance_records,
        'is_admin': request.user.role == 'admin',
        'is_center': is_center,
    }
    return render(request, 'reports/reports_dashboard.html', context)


@login_required
def student_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            students = StudentProfile.objects.none()
            courses = Course.objects.none()
            batches = Batch.objects.none()
        else:
            students = StudentProfile.objects.filter(batch__course__center=center)
            courses = Course.objects.filter(center=center)
            batches = Batch.objects.filter(course__center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        students = StudentProfile.objects.filter(batch__teacher=teacher_profile)
        courses = Course.objects.filter(batch__teacher=teacher_profile).distinct()
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:
        students = StudentProfile.objects.all()
        courses = Course.objects.all()
        batches = Batch.objects.all()

    query = request.GET.get('q', '').strip()
    selected_course = request.GET.get('course', '').strip()
    selected_batch = request.GET.get('batch', '').strip()

    if query:
        students = students.filter(full_name__icontains=query)
    if selected_course:
        students = students.filter(batch__course_id=selected_course)
    if selected_batch:
        students = students.filter(batch_id=selected_batch)

    # Calculate metrics
    total_students = students.count()
    active_students = students.filter(user__is_active=True).count()
    inactive_students = students.filter(user__is_active=False).count()

    course_counts = list(students.values('batch__course__name').annotate(count=Count('id')).order_by('batch__course__name'))
    batch_counts = list(students.values('batch__name').annotate(count=Count('id')).order_by('batch__name'))

    students = students.select_related('batch', 'batch__course').order_by('full_name')

    # Prefetch/Aggregated maps to prevent N+1 queries
    if is_center and center:
        att_stats = Attendance.objects.filter(batch__course__center=center).values('student_id').annotate(
            total=Count('id'), 
            present=Count('id', filter=Q(status='present'))
        )
        fee_stats = FeePayment.objects.filter(student__batch__course__center=center).values('student_id').annotate(total=Sum('amount'))
        attempt_stats = StudentExamAttempt.objects.filter(student__studentprofile__batch__course__center=center, is_completed=True).values('student_id').annotate(total=Count('id'))
        cert_stats = Certificate.objects.filter(course__center=center).values('student_id').annotate(total=Count('id'))
    elif is_teacher and teacher_profile:
        att_stats = Attendance.objects.filter(batch__teacher=teacher_profile).values('student_id').annotate(
            total=Count('id'), 
            present=Count('id', filter=Q(status='present'))
        )
        fee_stats = FeePayment.objects.filter(student__batch__teacher=teacher_profile).values('student_id').annotate(total=Sum('amount'))
        attempt_stats = StudentExamAttempt.objects.filter(student__studentprofile__batch__teacher=teacher_profile, is_completed=True).values('student_id').annotate(total=Count('id'))
        cert_stats = Certificate.objects.filter(batch__teacher=teacher_profile).values('student_id').annotate(total=Count('id'))
    else:
        att_stats = Attendance.objects.values('student_id').annotate(
            total=Count('id'), 
            present=Count('id', filter=Q(status='present'))
        )
        fee_stats = FeePayment.objects.values('student_id').annotate(total=Sum('amount'))
        attempt_stats = StudentExamAttempt.objects.filter(is_completed=True).values('student_id').annotate(total=Count('id'))
        cert_stats = Certificate.objects.values('student_id').annotate(total=Count('id'))

    att_map = {a['student_id']: (a['total'], a['present']) for a in att_stats}
    fee_map = {f['student_id']: f['total'] or Decimal('0.00') for f in fee_stats}
    attempt_map = {a['student_id']: a['total'] for a in attempt_stats}
    cert_map = {c['student_id']: c['total'] for c in cert_stats}

    students_data = []
    for s in students:
        total_att, present_att = att_map.get(s.id, (0, 0))
        attendance_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0.0

        paid_amount = fee_map.get(s.id, Decimal('0.00'))
        course_fee = Decimal(str(s.batch.course.fees)) if (s.batch and s.batch.course) else Decimal('0.00')
        pending_amount = course_fee - paid_amount
        if paid_amount == 0:
            fee_status = 'PENDING'
        elif pending_amount <= 0:
            fee_status = 'PAID'
        else:
            fee_status = 'PARTIAL'

        exams_attempted = attempt_map.get(s.user_id, 0)
        certs_count = cert_map.get(s.id, 0)

        students_data.append({
            'student': s,
            'attendance_pct': attendance_pct,
            'fee_status': fee_status,
            'exams_attempted': exams_attempted,
            'certificates_count': certs_count
        })

    # CSV Export (Feature 7)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="student_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Batch', 'Course', 'Attendance %', 'Fee Status', 'Exams Attempted', 'Certificates'])
        for item in students_data:
            writer.writerow([
                item['student'].full_name,
                item['student'].batch.name if item['student'].batch else 'Not Enrolled',
                item['student'].batch.course.name if (item['student'].batch and item['student'].batch.course) else '-',
                f"{item['attendance_pct']}%",
                item['fee_status'],
                item['exams_attempted'],
                item['certificates_count']
            ])
        return response

    return render(request, 'reports/student_report.html', {
        'students_data': students_data,
        'query': query,
        'courses': courses,
        'batches': batches,
        'selected_course': selected_course,
        'selected_batch': selected_batch,
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'course_counts': course_counts,
        'batch_counts': batch_counts,
    })


@login_required
def batch_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            batches = Batch.objects.none()
        else:
            batches = Batch.objects.filter(course__center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:
        batches = Batch.objects.all()

    query = request.GET.get('q', '').strip()
    if query:
        batches = batches.filter(name__icontains=query)

    batches = batches.select_related('course', 'teacher').order_by('name')

    student_stats = StudentProfile.objects.values('batch_id').annotate(total=Count('id'))
    student_map = {s['batch_id']: s['total'] for s in student_stats if s['batch_id']}

    att_stats = Attendance.objects.values('student__batch_id').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present'))
    )
    att_map = {a['student__batch_id']: (a['total'], a['present']) for a in att_stats if a['student__batch_id']}

    from django.db.models import Subquery, OuterRef
    student_profile_batch = StudentProfile.objects.filter(
        user__username=OuterRef('student__enrollment_no')
    ).values('batch_id')[:1]
    
    cert_stats = Certificate.objects.annotate(
        batch_id=Subquery(student_profile_batch)
    ).values('batch_id').annotate(total=Count('id'))
    cert_map = {c['batch_id']: c['total'] for c in cert_stats if c['batch_id']}

    batches_data = []
    for b in batches:
        total_students = student_map.get(b.id, 0)
        total_att, present_att = att_map.get(b.id, (0, 0))
        attendance_pct = round((present_att / total_att * 100), 1) if total_att > 0 else 0.0
        certs_issued = cert_map.get(b.id, 0)

        batches_data.append({
            'batch': b,
            'total_students': total_students,
            'attendance_pct': attendance_pct,
            'certificates_issued': certs_issued
        })

    return render(request, 'reports/batch_report.html', {
        'batches_data': batches_data,
        'query': query
    })


@login_required
def teacher_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            teachers = TeacherProfile.objects.none()
        else:
            teachers = TeacherProfile.objects.filter(batch__course__center=center).distinct()
    elif is_teacher:
        teachers = TeacherProfile.objects.filter(user=request.user)
    else:
        teachers = TeacherProfile.objects.all()

    query = request.GET.get('q', '').strip()
    if query:
        teachers = teachers.filter(full_name__icontains=query)

    teachers = teachers.order_by('full_name')

    batches_by_teacher = {}
    for b in Batch.objects.filter(teacher__isnull=False).select_related('course'):
        batches_by_teacher.setdefault(b.teacher_id, []).append(b)

    student_stats = StudentProfile.objects.filter(batch__teacher__isnull=False).values('batch__teacher_id').annotate(total=Count('id'))
    student_map = {s['batch__teacher_id']: s['total'] for s in student_stats}

    att_stats = Attendance.objects.filter(batch__teacher__isnull=False).values('batch__teacher_id').annotate(total=Count('id'))
    att_map = {a['batch__teacher_id']: a['total'] for a in att_stats}

    exam_stats = Exam.objects.filter(batches__teacher__isnull=False).values('batches__teacher_id').annotate(total=Count('id', distinct=True))
    exam_map = {e['batches__teacher_id']: e['total'] for e in exam_stats}

    teachers_data = []
    for t in teachers:
        assigned_batches = batches_by_teacher.get(t.id, [])
        total_students = student_map.get(t.id, 0)
        total_att = att_map.get(t.id, 0)
        total_exams = exam_map.get(t.id, 0)

        teachers_data.append({
            'teacher': t,
            'assigned_batches': assigned_batches,
            'total_students': total_students,
            'total_attendance_records': total_att,
            'total_exams': total_exams
        })

    return render(request, 'reports/teacher_report.html', {
        'teachers_data': teachers_data,
        'query': query
    })


@login_required
def attendance_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    # Filter inputs
    selected_batch = request.GET.get('batch', '')
    selected_date_range = request.GET.get('date', '').strip()

    # Determine Batches available for select
    if is_center:
        center = request.user.center
        if not center:
            batches = Batch.objects.none()
        else:
            batches = Batch.objects.filter(course__center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:
        batches = Batch.objects.all()

    # Process Date Range
    start_date = None
    end_date = None
    dates = []
    
    if selected_date_range:
        parts = selected_date_range.split('-')
        if len(parts) == 2:
            try:
                start_date = datetime.date.fromisoformat(parts[0].strip())
                end_date = datetime.date.fromisoformat(parts[1].strip())
            except ValueError:
                messages.error(request, "Invalid date range format. Use YYYY-MM-DD - YYYY-MM-DD.")
        elif len(parts) == 3: # In case someone types a single date with dashes and it splits wrong, but fromisoformat handles YYYY-MM-DD. Oh wait, if the range is 'YYYY-MM-DD - YYYY-MM-DD', splitting by '-' yields 6 parts!
            # Better parsing strategy for '2026-06-05 - 2026-07-04'
            pass
            
    # Better date parsing
    if selected_date_range:
        if ' - ' in selected_date_range:
            parts = selected_date_range.split(' - ')
            if len(parts) == 2:
                try:
                    start_date = datetime.date.fromisoformat(parts[0].strip())
                    end_date = datetime.date.fromisoformat(parts[1].strip())
                except ValueError:
                    messages.error(request, "Invalid date range format.")
        else:
            try:
                start_date = datetime.date.fromisoformat(selected_date_range.strip())
                end_date = start_date
            except ValueError:
                messages.error(request, "Invalid date format.")

    if not start_date or not end_date:
        end_date = datetime.date.today()
        start_date = end_date - datetime.timedelta(days=6)
        
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Generate dates list
    delta = end_date - start_date
    for i in range(delta.days + 1):
        dates.append(start_date + datetime.timedelta(days=i))

    students = []
    students_data = []
    
    if selected_batch:
        try:
            batch_obj = batches.get(id=selected_batch)
            students_qs = StudentProfile.objects.filter(batch=batch_obj).order_by('full_name')
            students = list(students_qs)
            
            # Fetch Attendance
            attendances = Attendance.objects.filter(
                batch=batch_obj,
                date__gte=start_date,
                date__lte=end_date
            )
            
            # Initialize matrix
            matrix = {}
            for student in students:
                matrix[student.id] = {d: '-' for d in dates}
                
            for att in attendances:
                if att.student_id in matrix and att.date in matrix[att.student_id]:
                    # Map status to code
                    if att.status == 'present':
                        code = 'P'
                    elif att.status == 'late':
                        code = 'L'
                    elif att.status == 'absent':
                        code = 'A'
                    elif att.status == 'holiday':
                        code = 'H'
                    elif att.status == 'half_day':
                        code = 'F'
                    else:
                        code = 'O' # Other
                    matrix[att.student_id][att.date] = code
                    
            for student in students:
                statuses = []
                for d in dates:
                    statuses.append(matrix[student.id][d])
                students_data.append({
                    'name': student.full_name,
                    'statuses': statuses
                })
                    
        except Batch.DoesNotExist:
            messages.error(request, "Selected timetable not found or access denied.")

    return render(request, 'reports/attendance_report.html', {
        'batches': batches,
        'selected_batch': selected_batch,
        'selected_date_range': selected_date_range if selected_date_range else f"{start_date.isoformat()} - {end_date.isoformat()}",
        'dates': dates,
        'students_data': students_data,
    })


@login_required
def fee_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            students = StudentProfile.objects.none()
            batches = Batch.objects.none()
            courses = Course.objects.none()
        else:
            students = StudentProfile.objects.filter(batch__course__center=center)
            batches = Batch.objects.filter(course__center=center)
            courses = Course.objects.filter(center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        students = StudentProfile.objects.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
        courses = Course.objects.filter(batch__teacher=teacher_profile).distinct()
    else:
        students = StudentProfile.objects.all()
        batches = Batch.objects.all()
        courses = Course.objects.all()

    selected_course = request.GET.get('course')
    selected_batch = request.GET.get('batch')
    selected_student = request.GET.get('student')

    if selected_course:
        students = students.filter(batch__course_id=selected_course)
    if selected_batch:
        students = students.filter(batch_id=selected_batch)
    if selected_student:
        students = students.filter(id=selected_student)

    students = students.select_related('batch', 'batch__course').order_by('full_name')

    # Total Fees Collected from these selected students
    payments = FeePayment.objects.filter(student__in=students)
    total_fees_collected = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    total_course_fees = students.aggregate(total=Sum('batch__course__fees'))['total'] or Decimal('0.00')
    total_pending_fees = Decimal(str(total_course_fees)) - Decimal(str(total_fees_collected))

    paid_map = {p['student_id']: p['total'] or Decimal('0.00') for p in FeePayment.objects.filter(student__in=students).values('student_id').annotate(total=Sum('amount'))}

    paid_count = 0
    pending_count = 0
    students_data = []

    for s in students:
        paid = paid_map.get(s.id, Decimal('0.00'))
        course_fee = Decimal(str(s.batch.course.fees)) if (s.batch and s.batch.course) else Decimal('0.00')
        pending = course_fee - paid
        if paid >= course_fee:
            paid_count += 1
            status = 'PAID'
        else:
            pending_count += 1
            status = 'PENDING'

        students_data.append({
            'student': s,
            'course_fee': course_fee,
            'paid': paid,
            'pending': pending,
            'status': status
        })

    # Available student options for filtering
    if is_center and center:
        filter_students = StudentProfile.objects.filter(batch__course__center=center)
    elif is_teacher and teacher_profile:
        filter_students = StudentProfile.objects.filter(batch__teacher=teacher_profile)
    else:
        filter_students = StudentProfile.objects.all()

    # CSV Export (Feature 7)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="fee_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Course', 'Batch', 'Paid Amount', 'Pending Amount', 'Status'])
        for item in students_data:
            writer.writerow([
                item['student'].full_name,
                item['student'].batch.course.name if (item['student'].batch and item['student'].batch.course) else '-',
                item['student'].batch.name if item['student'].batch else 'Not Enrolled',
                f"₹{item['paid']}",
                f"₹{item['pending']}",
                item['status']
            ])
        return response

    collection_pct = round((float(total_fees_collected) / float(total_course_fees) * 100), 1) if total_course_fees > 0 else 0.0

    return render(request, 'reports/fee_report.html', {
        'students_data': students_data,
        'batches': batches,
        'courses': courses,
        'students': filter_students,
        'total_fees_collected': total_fees_collected,
        'total_pending_fees': total_pending_fees,
        'paid_count': paid_count,
        'pending_count': pending_count,
        'selected_batch': selected_batch,
        'selected_course': selected_course,
        'selected_student': selected_student,
        'collection_pct': collection_pct
    })


@login_required
def exam_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            exams = Exam.objects.none()
            batches = Batch.objects.none()
        else:
            exams = Exam.objects.filter(batches__course__center=center).distinct()
            batches = Batch.objects.filter(course__center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        exams = Exam.objects.filter(batches__teacher=teacher_profile).distinct()
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:
        exams = Exam.objects.all()
        batches = Batch.objects.all()

    selected_exam_id = request.GET.get('exam', '').strip()
    selected_batch_id = request.GET.get('batch', '').strip()

    if selected_exam_id:
        if is_center and not exams.filter(id=selected_exam_id).exists():
            return HttpResponseForbidden("Access Denied.")
        exams = exams.filter(id=selected_exam_id)
    if selected_batch_id:
        if is_center and not batches.filter(id=selected_batch_id).exists():
            return HttpResponseForbidden("Access Denied.")
        exams = exams.filter(batches__id=selected_batch_id)

    # Calculate metrics
    total_exams = exams.count()
    active_exams = exams.filter(is_published=True).count()
    completed_exams = exams.filter(attempts__is_completed=True).distinct().count()

    attempts_qs = StudentExamAttempt.objects.filter(exam__in=exams)
    if is_center and center:
        attempts_qs = attempts_qs.filter(student__studentprofile__batch__course__center=center)
    elif is_teacher and teacher_profile:
        attempts_qs = attempts_qs.filter(student__studentprofile__batch__teacher=teacher_profile)

    total_attempts = attempts_qs.count()
    completed_attempts = attempts_qs.filter(is_completed=True)
    
    avg_score = completed_attempts.aggregate(avg=Avg('score'))['avg'] or 0.0
    highest_score = completed_attempts.aggregate(highest=Max('score'))['highest'] or 0.0
    lowest_score = completed_attempts.aggregate(lowest=Min('score'))['lowest'] or 0.0
    
    total_comp = completed_attempts.count()
    passed_comp = completed_attempts.filter(score__gte=F('exam__pass_percentage')).count()
    pass_pct = round((passed_comp / total_comp * 100), 1) if total_comp > 0 else 0.0

    exams = exams.order_by('-date', 'title')

    attempt_stats = attempts_qs.filter(is_completed=True).values('exam_id').annotate(
        total_attempts=Count('id'),
        avg_score=Avg('score'),
        passed_attempts=Count('id', filter=Q(score__gte=F('exam__pass_percentage')))
    )
    attempt_map = {
        a['exam_id']: {
            'total': a['total_attempts'],
            'avg_score': round(a['avg_score'], 1) if a['avg_score'] is not None else 0.0,
            'pass_pct': round((a['passed_attempts'] / a['total_attempts'] * 100), 1) if a['total_attempts'] > 0 else 0.0
        } for a in attempt_stats
    }

    batches_by_exam = {}
    for b in Batch.objects.filter(exams__in=exams).prefetch_related('exams'):
        for e in b.exams.all():
            batches_by_exam.setdefault(e.id, []).append(b)

    exams_data = []
    for e in exams:
        assigned_batches = batches_by_exam.get(e.id, [])
        stats = attempt_map.get(e.id, {'total': 0, 'avg_score': 0.0, 'pass_pct': 0.0})

        exams_data.append({
            'exam': e,
            'assigned_batches': assigned_batches,
            'total_attempts': stats['total'],
            'avg_score': stats['avg_score'],
            'pass_pct': stats['pass_pct']
        })

    # CSV Export (Feature 7)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exam_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Exam Title', 'Assigned Batches', 'Total Attempts', 'Average Score (%)', 'Pass Percentage (%)'])
        for item in exams_data:
            batch_names = ", ".join([b.name for b in item['assigned_batches']])
            writer.writerow([
                item['exam'].title,
                batch_names,
                item['total_attempts'],
                f"{item['avg_score']}%",
                f"{item['pass_pct']}%"
            ])
        return response

    return render(request, 'reports/exam_report.html', {
        'exams_data': exams_data,
        'exams': exams,
        'batches': batches,
        'selected_exam': selected_exam_id,
        'selected_batch': selected_batch_id,
        'total_exams': total_exams,
        'active_exams': active_exams,
        'completed_exams': completed_exams,
        'total_attempts': total_attempts,
        'avg_score': round(avg_score, 1),
        'highest_score': round(highest_score, 1),
        'lowest_score': round(lowest_score, 1),
        'pass_pct': pass_pct
    })


@login_required
def certificate_report(request):
    if request.user.role not in ('admin', 'teacher', 'center'):
        return HttpResponseForbidden("Access Denied.")

    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if is_center:
        center = request.user.center
        if not center:
            certs = Certificate.objects.none()
            batches = Batch.objects.none()
            courses = Course.objects.none()
            student_qs = StudentProfile.objects.none()
        else:
            certs = Certificate.objects.filter(course__center=center)
            batches = Batch.objects.filter(course__center=center)
            courses = Course.objects.filter(center=center)
            student_qs = StudentProfile.objects.filter(batch__course__center=center)
    elif is_teacher:
        teacher_profile = get_teacher_profile(request.user)
        if not teacher_profile:
            return HttpResponseForbidden("Access Denied: Teacher profile missing.")
        # Filter certificates by students belonging to this teacher's batches
        teacher_student_usernames = StudentProfile.objects.filter(
            batch__teacher=teacher_profile
        ).values_list('user__username', flat=True)
        certs = Certificate.objects.filter(student__enrollment_no__in=teacher_student_usernames)
        batches = Batch.objects.filter(teacher=teacher_profile)
        courses = Course.objects.filter(batch__teacher=teacher_profile).distinct()
        student_qs = StudentProfile.objects.filter(batch__teacher=teacher_profile)
    else:
        certs = Certificate.objects.all()
        batches = Batch.objects.all()
        courses = Course.objects.all()
        student_qs = StudentProfile.objects.all()

    selected_batch = request.GET.get('batch')
    selected_course = request.GET.get('course')
    selected_status = request.GET.get('status')

    if selected_batch:
        enrolled_usernames = StudentProfile.objects.filter(batch_id=selected_batch).values_list('user__username', flat=True)
        certs = certs.filter(student__enrollment_no__in=enrolled_usernames)
        student_qs = student_qs.filter(batch_id=selected_batch)
    if selected_course:
        certs = certs.filter(course_id=selected_course)
        student_qs = student_qs.filter(batch__course_id=selected_course)
    if selected_status:
        if selected_status == 'issued':
            pass
        elif selected_status == 'revoked':
            certs = certs.none()
        else:
            certs = certs.none()

    total_certs = certs.count()
    certs_issued_count = total_certs
    certs_revoked_count = 0

    # Eligible Students Calculation
    students_stats = student_qs.annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'))
    ).select_related('batch', 'batch__course')

    if is_center and center:
        att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.filter(batch__course__center=center).values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}
    elif is_teacher and teacher_profile:
        att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.filter(batch__teacher=teacher_profile).values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}
    else:
        att_map = {a['student_id']: (a['total'], a['present']) for a in Attendance.objects.values('student_id').annotate(total=Count('id'), present=Count('id', filter=Q(status='present')))}

    eligible_students_count = 0
    for student in students_stats:
        course_fee = Decimal(str(student.batch.course.fees)) if (student.batch and student.batch.course) else Decimal('0.00')
        fee_eligible = student.paid_amount >= course_fee
        
        total_att, present_att = att_map.get(student.id, (0, 0))
        student_att_pct = (present_att / total_att) * 100 if total_att > 0 else 0.0
        attendance_eligible = student_att_pct >= 75.0
        
        if fee_eligible and attendance_eligible:
            eligible_students_count += 1

    from django.db.models import Subquery, OuterRef
    student_profile_batch_name = StudentProfile.objects.filter(
        user__username=OuterRef('student__enrollment_no')
    ).values('batch__name')[:1]

    certs = certs.select_related('student', 'course').annotate(
        student_batch_name=Subquery(student_profile_batch_name)
    ).order_by('-issue_date', 'student__student_name')

    # CSV Export (Feature 7)
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="certificate_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Certificate Number', 'Student Name', 'Course', 'Batch', 'Issue Date', 'Status'])
        for cert in certs:
            writer.writerow([
                cert.certificate_number,
                cert.student.student_name,
                cert.course.name,
                cert.student_batch_name or '-',
                cert.issue_date.strftime('%Y-%m-%d'),
                'Active'
            ])
        return response

    return render(request, 'reports/certificate_report.html', {
        'certs': certs,
        'batches': batches,
        'courses': courses,
        'selected_batch': selected_batch,
        'selected_course': selected_course,
        'selected_status': selected_status,
        'total_certs': total_certs,
        'certs_issued_count': certs_issued_count,
        'certs_revoked_count': certs_revoked_count,
        'eligible_students_count': eligible_students_count
    })
