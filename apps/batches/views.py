from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from apps.courses.models import Course
from apps.teachers.models import TeacherProfile
from .models import Batch
from .forms import BatchForm


@login_required
def batch_list(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    if request.user.role == 'center':
        if not request.user.center:
            batches = Batch.objects.none()
        else:
            batches = Batch.objects.filter(course__center=request.user.center).select_related('course', 'teacher').annotate(student_count=Count('studentprofile'))
    else:
        batches = Batch.objects.all().select_related('course', 'teacher').annotate(student_count=Count('studentprofile'))
        
    return render(request, 'batches/batch_list.html', {'batches': batches})


@login_required
def batch_detail(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    batch = get_object_or_404(Batch.objects.select_related('course', 'teacher'), pk=pk)
    
    if request.user.role == 'center' and batch.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's batches.")
        
    students = batch.studentprofile_set.all()
    exams = batch.exams.all()
    
    from django.db.models import Q, Count
    attendance_history = batch.attendances.values('date').annotate(
        present_count=Count('id', filter=Q(status='present')),
        absent_count=Count('id', filter=Q(status='absent'))
    ).order_by('-date')
    
    return render(request, 'batches/batch_detail.html', {
        'batch': batch,
        'students': students,
        'exams': exams,
        'attendance_history': attendance_history
    })


@login_required
def batch_create(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if request.user.role == 'center':
            if not request.user.center:
                form.fields['course'].queryset = Course.objects.none()
                form.fields['teacher'].queryset = TeacherProfile.objects.none()
            else:
                form.fields['course'].queryset = Course.objects.filter(center=request.user.center)
                form.fields['teacher'].queryset = TeacherProfile.objects.filter(
                    Q(batch__course__center=request.user.center) | Q(batch__isnull=True)
                ).distinct()
        if form.is_valid():
            if request.user.role == 'center':
                course = form.cleaned_data.get('course')
                if not request.user.center or course.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: You cannot assign batch to other center's course.")
            form.save()
            messages.success(request, 'Batch created successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm()
        if request.user.role == 'center':
            if not request.user.center:
                form.fields['course'].queryset = Course.objects.none()
                form.fields['teacher'].queryset = TeacherProfile.objects.none()
            else:
                form.fields['course'].queryset = Course.objects.filter(center=request.user.center)
                form.fields['teacher'].queryset = TeacherProfile.objects.filter(
                    Q(batch__course__center=request.user.center) | Q(batch__isnull=True)
                ).distinct()
                
    return render(request, 'batches/batch_form.html', {'form': form, 'action': 'Create'})


@login_required
def batch_update(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    batch = get_object_or_404(Batch, pk=pk)
    
    if request.user.role == 'center' and batch.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's batches.")
        
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if request.user.role == 'center':
            if not request.user.center:
                form.fields['course'].queryset = Course.objects.none()
                form.fields['teacher'].queryset = TeacherProfile.objects.none()
            else:
                form.fields['course'].queryset = Course.objects.filter(center=request.user.center)
                form.fields['teacher'].queryset = TeacherProfile.objects.filter(
                    Q(batch__course__center=request.user.center) | Q(batch__isnull=True)
                ).distinct()
        if form.is_valid():
            if request.user.role == 'center':
                course = form.cleaned_data.get('course')
                if not request.user.center or course.center != request.user.center:
                    return HttpResponseForbidden("Access Denied: You cannot assign batch to other center's course.")
            form.save()
            messages.success(request, 'Batch updated successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm(instance=batch)
        if request.user.role == 'center':
            if not request.user.center:
                form.fields['course'].queryset = Course.objects.none()
                form.fields['teacher'].queryset = TeacherProfile.objects.none()
            else:
                form.fields['course'].queryset = Course.objects.filter(center=request.user.center)
                form.fields['teacher'].queryset = TeacherProfile.objects.filter(
                    Q(batch__course__center=request.user.center) | Q(batch__isnull=True)
                ).distinct()
                
    return render(request, 'batches/batch_form.html', {'form': form, 'action': 'Update', 'batch': batch})


@login_required
def batch_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    batch = get_object_or_404(Batch, pk=pk)
    
    if request.user.role == 'center' and batch.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's batches.")
        
    if request.method == 'POST':
        batch.delete()
        messages.success(request, 'Batch deleted successfully.')
        return redirect('batch_list')
    return render(request, 'batches/batch_confirm_delete.html', {'batch': batch})

