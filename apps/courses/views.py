from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.views import admin_required
from .models import Course
from .forms import CourseForm


@admin_required
def course_list(request):
    courses = Course.objects.all().select_related('center')
    return render(request, 'courses/course_list.html', {'courses': courses})


@admin_required
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course created successfully.')
            return redirect('course_list')
    else:
        form = CourseForm()
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Create'})


@admin_required
def course_update(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Course updated successfully.')
            return redirect('course_list')
    else:
        form = CourseForm(instance=course)
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Update', 'course': course})


@admin_required
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('course_list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})
