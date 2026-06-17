import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Count, Q
from datetime import date as datetime_date
from apps.batches.models import Batch
from apps.students.models import StudentProfile
from apps.teachers.models import TeacherProfile
from .models import Attendance


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
        if not center or batch.course.center != center:
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
        
    attendances = Attendance.objects.all().select_related('student', 'batch', 'batch__course', 'marked_by')
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        attendances = attendances.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
        students = StudentProfile.objects.filter(batch__in=batches)
    elif is_center:
        center = request.user.center
        if not center:
            attendances = Attendance.objects.none()
            batches = Batch.objects.none()
            students = StudentProfile.objects.none()
        else:
            attendances = attendances.filter(batch__course__center=center)
            batches = Batch.objects.filter(course__center=center)
            students = StudentProfile.objects.filter(batch__course__center=center)
    else:
        batches = Batch.objects.all()
        students = StudentProfile.objects.all()
        
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
        
    attendances = attendances.order_by('-date', 'student__full_name')
    
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
                att.student.full_name,
                att.batch.name,
                att.batch.course.name,
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
            student_obj = get_object_or_404(StudentProfile, id=student_id, batch__course__center=request.user.center)
        else:
            student_obj = get_object_or_404(StudentProfile, id=student_id)
            
        if student_obj.batch:
            initial['student'] = student_obj
            initial['batch'] = student_obj.batch
            
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
                'student_name': student_obj.full_name,
                'batch_name': student_obj.batch.name,
                'course_name': student_obj.batch.course.name if student_obj.batch.course else '-',
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
        if not attendance.batch or not attendance.batch.course or attendance.batch.course.center != request.user.center:
            return HttpResponseForbidden("Access Denied: You cannot manage attendance for another center.")
            
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
        'student_name': student_obj.full_name,
        'batch_name': attendance.batch.name if attendance.batch else '-',
        'course_name': attendance.batch.course.name if (attendance.batch and attendance.batch.course) else '-',
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
