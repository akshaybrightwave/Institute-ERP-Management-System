from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
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
    
    if not (is_admin or is_teacher):
        return HttpResponseForbidden("Access Denied: Admins or Teachers only.")
    
    batch = get_object_or_404(Batch, pk=batch_id)
    teacher_profile = None
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        if batch.teacher != teacher_profile:
            return HttpResponseForbidden("Access Denied: You are not the assigned teacher for this batch.")
            
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
    
    if not (is_admin or is_teacher):
        return HttpResponseForbidden("Access Denied: Admins or Teachers only.")
        
    attendances = Attendance.objects.all().select_related('student', 'batch', 'marked_by')
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        attendances = attendances.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
        students = StudentProfile.objects.filter(batch__in=batches)
    else:
        batches = Batch.objects.all()
        students = StudentProfile.objects.all()
        
    batch_id = request.GET.get('batch')
    student_id = request.GET.get('student')
    date_filter = request.GET.get('date')
    
    if batch_id:
        attendances = attendances.filter(batch_id=batch_id)
    if student_id:
        attendances = attendances.filter(student_id=student_id)
    if date_filter:
        attendances = attendances.filter(date=date_filter)
        
    attendances = attendances.order_by('-date', 'student__full_name')
    
    paginator = Paginator(attendances, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'attendance/attendance_list.html', {
        'page_obj': page_obj,
        'batches': batches,
        'students': students,
        'selected_batch': batch_id,
        'selected_student': student_id,
        'selected_date': date_filter,
    })
