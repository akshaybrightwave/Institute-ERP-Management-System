import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from datetime import date as datetime_date
from apps.batches.models import Batch
from apps.students.models import StudentProfile
from apps.students.models import StudentAdmission
from apps.teachers.models import TeacherProfile
from .models import Attendance


@login_required
def student_attendance(request):
    """New Student Attendance page — Select batch + date, then mark 5-option attendance with remarks."""
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if not (is_admin or is_teacher or is_center):
        return HttpResponseForbidden("Access Denied: Admins, Center users, or Teachers only.")

    from apps.academics.models import TimeTable
    batches = TimeTable.objects.all()

    selected_batch_id = request.GET.get('batch') or request.POST.get('batch')
    selected_date_str = request.GET.get('date') or request.POST.get('date')

    # Parse date
    if selected_date_str:
        try:
            selected_date = datetime_date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = datetime_date.today()
    else:
        selected_date = datetime_date.today()

    selected_batch = None
    student_list = []
    searched = False

    if selected_batch_id:
        try:
            selected_batch = TimeTable.objects.get(pk=selected_batch_id)
        except TimeTable.DoesNotExist:
            return HttpResponseForbidden("Access Denied: Time Table not accessible.")

    if request.method == 'POST' and selected_batch:
        # ── SAVE attendance using StudentAdmission directly ──
        teacher_profile_obj = None
        if is_teacher:
            teacher_profile_obj = get_object_or_404(TeacherProfile, user=request.user)

        from apps.students.models import StudentAdmission
        admissions = StudentAdmission.objects.filter(
            timetable_course=selected_batch.timetable_name
        ).order_by('student_name')

        saved_count = 0
        for admission in admissions:
            status = request.POST.get(f'status_{admission.id}', 'present')
            remark = request.POST.get(f'remark_{admission.id}', '').strip()
            if status not in ['present', 'late', 'absent', 'holiday', 'half_day']:
                status = 'present'
            Attendance.objects.update_or_create(
                student=admission,
                timetable_name=selected_batch.timetable_name,
                date=selected_date,
                defaults={
                    'status': status,
                    'remark': remark,
                    'marked_by': teacher_profile_obj if is_teacher else None,
                }
            )
            saved_count += 1

        messages.success(request, f"Attendance saved successfully for {saved_count} student(s) on {selected_date.strftime('%d-%m-%Y')}.")
        return redirect(f"{request.path}?batch={selected_batch.pk}&date={selected_date.isoformat()}")

    # ── GET: load students if batch selected ──
    if selected_batch and request.GET.get('batch'):
        searched = True
        from apps.students.models import StudentAdmission
        admissions = StudentAdmission.objects.filter(
            timetable_course=selected_batch.timetable_name
        ).order_by('student_name')

        existing = {
            att.student_id: att
            for att in Attendance.objects.filter(
                timetable_name=selected_batch.timetable_name,
                date=selected_date
            )
        }

        for idx, admission in enumerate(admissions, start=1):
            att = existing.get(admission.id)
            student_list.append({
                'idx': idx,
                'student': admission,
                'enrollment_no': admission.enrollment_no,
                'status': att.status if att else 'present',
                'remark': att.remark if att else '',
            })

    return render(request, 'attendance/student_attendance.html', {
        'batches': batches,
        'selected_batch': selected_batch,
        'selected_batch_id': selected_batch_id,
        'selected_date': selected_date.isoformat(),
        'student_list': student_list,
        'searched': searched,
        'is_admin': is_admin,
        'is_teacher': is_teacher,
        'is_center': is_center,
    })




@login_required
def mark_attendance(request, batch_id):
    # Enforce role checks
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_teacher or is_center):
        return HttpResponseForbidden("Access Denied: Admins, Center users, or Teachers only.")
    
    batch = get_object_or_404(Batch, pk=batch_id)
    teacher_profile = None
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        if batch.teacher != teacher_profile:
            return HttpResponseForbidden("Access Denied: You are not the assigned teacher for this batch.")
    elif is_center:
        center = request.user.center
        if not center or batch.center != center:
            return HttpResponseForbidden("Access Denied: This batch does not belong to your center.")
            
    # Get selected date, defaulting to today
    selected_date_str = request.GET.get('date') or request.POST.get('date')
    if selected_date_str:
        try:
            selected_date = datetime_date.fromisoformat(selected_date_str)
        except ValueError:
            selected_date = datetime_date.today()
    else:
        selected_date = datetime_date.today()
        
    students = batch.studentprofile_set.all().order_by('full_name')
    
    # Fetch existing attendance for this date and batch to prepopulate
    existing_attendances = Attendance.objects.filter(batch=batch, date=selected_date)
    attendance_dict = {att.student_id: att.status for att in existing_attendances}
    
    if request.method == 'POST':
        for student in students:
            status = request.POST.get(f'status_{student.id}')
            if status in ['present', 'absent']:
                Attendance.objects.update_or_create(
                    student=student,
                    date=selected_date,
                    defaults={
                        'batch': batch,
                        'status': status,
                        'marked_by': teacher_profile if is_teacher else None
                    }
                )
        messages.success(request, f"Attendance saved successfully for {selected_date.strftime('%Y-%m-%d')}.")
        return redirect(f"{request.path}?date={selected_date.isoformat()}")
        
    student_list = []
    for student in students:
        student_list.append({
            'student': student,
            'status': attendance_dict.get(student.id, 'present')  # Default to present
        })
        
    return render(request, 'attendance/mark_attendance.html', {
        'batch': batch,
        'selected_date': selected_date.isoformat(),
        'student_list': student_list,
        'is_admin': is_admin
    })


@login_required
def attendance_list(request):
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_teacher or is_center):
        return HttpResponseForbidden("Access Denied: Admins, Center users, or Teachers only.")
        
    attendances = Attendance.objects.all().select_related(
        'student',
        'student__course',
        'student__center',
        'batch',
        'batch__course',
        'marked_by'
    )
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        attendances = attendances.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
        student_user_ids = StudentProfile.objects.filter(batch__in=batches).values_list('user_id', flat=True)
        students = StudentAdmission.objects.filter(user_id__in=student_user_ids).order_by('student_name')
    elif is_center:
        center = request.user.center
        if not center:
            attendances = Attendance.objects.none()
            batches = Batch.objects.none()
            students = StudentAdmission.objects.none()
        else:
            attendances = attendances.filter(student__center=center)
            batches = Batch.objects.filter(course__assignments__center=center, course__assignments__is_active=True)
            students = StudentAdmission.objects.filter(center=center, status='Approved').order_by('student_name')
    else:
        batches = Batch.objects.all()
        students = StudentAdmission.objects.filter(status='Approved').order_by('student_name')
        
    batch_id = request.GET.get('batch')
    student_id = request.GET.get('student')
    date_filter = request.GET.get('date')
    
    # URL level validation / Cross-center URL manipulation protection
    if is_center:
        if batch_id and not batches.filter(id=batch_id).exists():
            return HttpResponseForbidden("Access Denied: Batch does not belong to your center.")
        if student_id and not students.filter(id=student_id).exists():
            return HttpResponseForbidden("Access Denied: Student does not belong to your center.")
    elif is_teacher:
        if batch_id and not batches.filter(id=batch_id).exists():
            return HttpResponseForbidden("Access Denied: You are not assigned to this batch.")
        if student_id and not students.filter(id=student_id).exists():
            return HttpResponseForbidden("Access Denied: Student is not in your batches.")
            
    if batch_id:
        attendances = attendances.filter(batch_id=batch_id)
    if student_id:
        attendances = attendances.filter(student_id=student_id)
    if date_filter:
        attendances = attendances.filter(date=date_filter)
        
    attendances = attendances.order_by('-date', 'student__student_name')
    
    # CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="attendance_list.csv"'
        writer = csv.writer(response)
        writer.writerow(['Student Name', 'Batch', 'Course', 'Date', 'Status', 'Attendance %', 'Marked By'])
        
        all_student_ids = list(attendances.values_list('student_id', flat=True).distinct())
        stats = Attendance.objects.filter(student_id__in=all_student_ids).values('student_id').annotate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present'))
        )
        pct_map = {item['student_id']: round((item['present'] / item['total'] * 100), 1) if item['total'] > 0 else 0.0 for item in stats}
        
        for att in attendances:
            marked_by_name = att.marked_by.full_name if att.marked_by else 'Admin'
            student_pct = pct_map.get(att.student_id, 0.0)
            writer.writerow([
                att.student.student_name,
                att.batch.name if att.batch else (att.timetable_name or '-'),
                att.student.course.name if att.student.course else '-',
                att.date.strftime('%Y-%m-%d'),
                att.status.capitalize(),
                f"{student_pct}%",
                marked_by_name
            ])
        return response
    
    paginator = Paginator(attendances, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate attendance percentage for the students displayed on this page
    student_ids = [att.student_id for att in page_obj]
    stats = Attendance.objects.filter(student_id__in=student_ids).values('student_id').annotate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present'))
    )
    pct_map = {item['student_id']: round((item['present'] / item['total'] * 100), 1) if item['total'] > 0 else 0.0 for item in stats}
    
    for att in page_obj:
        att.student_attendance_pct = pct_map.get(att.student_id, 0.0)
        
    return render(request, 'attendance/attendance_list.html', {
        'page_obj': page_obj,
        'batches': batches,
        'students': students,
        'selected_batch': batch_id,
        'selected_student': student_id,
        'selected_date': date_filter,
    })


@login_required
def attendance_create(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Admins or Center users only.")
        
    from .forms import AttendanceForm
    
    student_id = request.GET.get('student')
    initial = {}
    student_obj = None
    student_summary = None
    
    if student_id:
        if request.user.role == 'center':
            student_obj = get_object_or_404(StudentAdmission, id=student_id, center=request.user.center)
        else:
            student_obj = get_object_or_404(StudentAdmission, id=student_id)
            
        initial['student'] = student_obj
            
        # Fetch summary card details
        att_stats = Attendance.objects.filter(student=student_obj).aggregate(
            total=Count('id'),
            present=Count('id', filter=Q(status='present')),
            absent=Count('id', filter=Q(status='absent'))
        )
        total = att_stats['total']
        present = att_stats['present']
        absent = att_stats['absent']
        pct = round((present / total * 100), 1) if total > 0 else 0.0

        student_summary = {
            'student_name': student_obj.student_name,
            'batch_name': student_obj.timetable_course or '-',
            'course_name': student_obj.course.name if student_obj.course else '-',
            'attendance_pct': pct,
            'present_count': present,
            'absent_count': absent
        }
            
    if request.method == 'POST':
        form = AttendanceForm(request.POST, user=request.user)
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.save()
            messages.success(request, "Attendance record created successfully.")
            return redirect('attendance_list')
    else:
        form = AttendanceForm(initial=initial, user=request.user)
        
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'action': 'Create',
        'student_summary': student_summary,
    })


@login_required
def attendance_edit(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Admins or Center users only.")
        
    attendance = get_object_or_404(Attendance, pk=pk)
    
    # Check center isolation
    if request.user.role == 'center':
        if attendance.student.center != request.user.center:
            return HttpResponseForbidden("Access Denied: You do not manage this student's attendance.")
            
    from .forms import AttendanceForm
    
    student_obj = attendance.student
    # Fetch summary card details
    att_stats = Attendance.objects.filter(student=student_obj).aggregate(
        total=Count('id'),
        present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent'))
    )
    total = att_stats['total']
    present = att_stats['present']
    absent = att_stats['absent']
    pct = round((present / total * 100), 1) if total > 0 else 0.0
    
    student_summary = {
        'student_name': student_obj.student_name,
        'batch_name': attendance.batch.name if attendance.batch else (attendance.timetable_name or student_obj.timetable_course or '-'),
        'course_name': student_obj.course.name if student_obj.course else '-',
        'attendance_pct': pct,
        'present_count': present,
        'absent_count': absent
    }
    
    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Attendance record updated successfully.")
            return redirect('attendance_list')
    else:
        form = AttendanceForm(instance=attendance, user=request.user)
        
    return render(request, 'attendance/attendance_form.html', {
        'form': form,
        'action': 'Edit',
        'student_summary': student_summary,
    })

@login_required
def attendance_by_date(request):
    """Attendance Report — pivot matrix by TimeTable + date range."""
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    is_center = request.user.role == 'center'

    if not (is_admin or is_teacher or is_center):
        return HttpResponseForbidden("Access Denied.")

    from apps.academics.models import TimeTable
    from apps.students.models import StudentAdmission

    timetables = TimeTable.objects.all().order_by('timetable_name')

    selected_tt_id = request.GET.get('timetable', '')
    date_range_str = request.GET.get('date_range', '')
    searched = False

    selected_timetable = None
    date_columns = []
    student_rows = []
    start_date = None
    end_date = None

    if selected_tt_id:
        try:
            selected_timetable = TimeTable.objects.get(pk=selected_tt_id)
        except TimeTable.DoesNotExist:
            selected_timetable = None

    if selected_timetable and date_range_str:
        # Parse date range "YYYY-MM-DD - YYYY-MM-DD"
        parts = [p.strip() for p in date_range_str.split(' - ')]
        try:
            start_date = datetime_date.fromisoformat(parts[0])
            end_date = datetime_date.fromisoformat(parts[1]) if len(parts) > 1 else start_date
        except (ValueError, IndexError):
            start_date = end_date = None

    if selected_timetable and start_date and end_date:
        searched = True
        # Build list of all dates in range
        from datetime import timedelta
        delta = (end_date - start_date).days
        date_columns = [start_date + timedelta(days=i) for i in range(delta + 1)]

        # Get all admissions for this timetable
        admissions = StudentAdmission.objects.filter(
            timetable_course=selected_timetable.timetable_name
        ).order_by('student_name')

        # Get all attendance records in this range for this timetable
        records = Attendance.objects.filter(
            timetable_name=selected_timetable.timetable_name,
            date__range=(start_date, end_date)
        ).values('student_id', 'date', 'status')

        # Build lookup: {student_id: {date: status}}
        att_lookup = {}
        for rec in records:
            att_lookup.setdefault(rec['student_id'], {})[rec['date']] = rec['status']

        STATUS_LETTER = {
            'present': 'P',
            'late': 'L',
            'absent': 'A',
            'holiday': 'H',
            'half_day': 'F',
        }
        STATUS_COLOR = {
            'present': '#10b981',
            'late': '#f59e0b',
            'absent': '#ef4444',
            'holiday': '#818cf8',
            'half_day': '#06b6d4',
        }

        for adm in admissions:
            day_data = []
            for d in date_columns:
                status = att_lookup.get(adm.id, {}).get(d, '')
                day_data.append({
                    'status': STATUS_LETTER.get(status, '—'),
                    'color': STATUS_COLOR.get(status, 'rgba(255,255,255,0.3)'),
                })
            student_rows.append({
                'name': adm.student_name,
                'enrollment': adm.enrollment_no,
                'days': day_data,
            })

    context = {
        'timetables': timetables,
        'selected_tt_id': selected_tt_id,
        'date_range_str': date_range_str,
        'searched': searched,
        'date_columns': date_columns,
        'student_rows': student_rows,
    }
    return render(request, 'attendance/attendance_by_date.html', context)
