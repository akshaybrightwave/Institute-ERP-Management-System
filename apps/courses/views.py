from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from .models import Course
from .forms import CourseForm


@login_required
def course_list(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
    
    if request.user.role == 'center':
        if not request.user.center:
            courses = Course.objects.none()
        else:
            courses = Course.objects.filter(center=request.user.center).select_related('center')
    else:
        courses = Course.objects.all().select_related('center')
        
    return render(request, 'courses/course_list.html', {'courses': courses})


@login_required
def course_create(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if request.user.role == 'center':
            from apps.centers.models import Center
            form.fields['center'].queryset = Center.objects.filter(id=request.user.center.id) if request.user.center else Center.objects.none()
        if form.is_valid():
            if request.user.role == 'center' and form.cleaned_data.get('center') != request.user.center:
                return HttpResponseForbidden("Access Denied: You cannot create courses for other centers.")
            form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('course_list')
    else:
        form = CourseForm()
        if request.user.role == 'center':
            from apps.centers.models import Center
            form.fields['center'].queryset = Center.objects.filter(id=request.user.center.id) if request.user.center else Center.objects.none()
            if request.user.center:
                form.fields['center'].initial = request.user.center
                
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Create'})


@login_required
def course_update(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    course = get_object_or_404(Course, pk=pk)
    if request.user.role == 'center' and course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
        
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if request.user.role == 'center':
            from apps.centers.models import Center
            form.fields['center'].queryset = Center.objects.filter(id=request.user.center.id) if request.user.center else Center.objects.none()
        if form.is_valid():
            if request.user.role == 'center' and form.cleaned_data.get('center') != request.user.center:
                return HttpResponseForbidden("Access Denied: You cannot assign courses to other centers.")
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
        if request.user.role == 'center':
            from apps.centers.models import Center
            form.fields['center'].queryset = Center.objects.filter(id=request.user.center.id) if request.user.center else Center.objects.none()
            
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Update', 'course': course})


@login_required
def course_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    course = get_object_or_404(Course, pk=pk)
    if request.user.role == 'center' and course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
        
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('course_list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})

