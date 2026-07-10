from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from .models import Course
from .forms import CourseForm
from apps.centers.models import CenterCourseAssignment


def _center_manages_course(user_center, course):
    """Return True if the user's center has this course assigned via CenterCourseAssignment."""
    return CenterCourseAssignment.objects.filter(center=user_center, course=course).exists()


@login_required
def course_list(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
    
    # Initialize form with logged-in user
    form = CourseForm(user=request.user)
    
    # Handle inline Create (POST)
    if request.method == 'POST':
        form = CourseForm(request.POST, user=request.user)
        if form.is_valid():
            course = form.save(commit=False)
            course.save()
            # If a center user creates a course, auto-assign it to their center
            if request.user.role == 'center' and request.user.center:
                CenterCourseAssignment.objects.get_or_create(
                    center=request.user.center,
                    course=course,
                    defaults={'assigned_by': request.user}
                )
            messages.success(request, 'Course created successfully.')
            return redirect('course_list')
        
    # Search and Filter
    query = request.GET.get('q', '').strip()
    if request.user.role == 'center':
        if not request.user.center:
            qs = Course.objects.none()
            deleted_qs = Course.all_objects.none()
        else:
            # Courses assigned to this center via CenterCourseAssignment
            assigned_course_ids = CenterCourseAssignment.objects.filter(
                center=request.user.center
            ).values_list('course_id', flat=True)
            qs = Course.objects.filter(id__in=assigned_course_ids).select_related('category')
            deleted_qs = Course.all_objects.filter(
                id__in=assigned_course_ids, is_deleted=True
            ).select_related('category')
    else:
        qs = Course.objects.all().select_related('category')
        deleted_qs = Course.all_objects.filter(is_deleted=True).select_related('category')
        
    if query:
        qs = qs.filter(name__icontains=query)
        deleted_qs = deleted_qs.filter(name__icontains=query)
        
    qs = qs.order_by('-id')
    deleted_courses = deleted_qs.order_by('-deleted_at', '-id')
    
    # Pagination (10 per page) for active courses
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))
        
    return render(request, 'courses/course_list.html', {
        'form': form,
        'page_obj': page_obj,
        'deleted_courses': deleted_courses,
        'query': query,
    })


@login_required
def course_create(request):
    return redirect('course_list')


@login_required
def course_update(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    course = get_object_or_404(Course.all_objects, pk=pk)
    if request.user.role == 'center' and not _center_manages_course(request.user.center, course):
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
        
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            name = request.POST.get('name', '').strip()
            fees = request.POST.get('fees', '').strip()
            
            if not name:
                return JsonResponse({'success': False, 'errors': {'name': ['Course name is required.']}})
                
            # Duplicate check by name
            qs = Course.objects.filter(name__iexact=name).exclude(pk=course.pk)
            if qs.exists():
                return JsonResponse({'success': False, 'errors': {'name': ['Course with this name already exists.']}})
                
            course.name = name
            if fees:
                try:
                    course.fees = float(fees)
                except ValueError:
                    return JsonResponse({'success': False, 'errors': {'fees': ['Invalid fee format.']}})
            else:
                course.fees = None
                
            course.save()
            return JsonResponse({'success': True})
            
        # GET request: return details
        return JsonResponse({
            'name': course.name,
            'fees': float(course.fees) if course.fees else 0.0,
        })
        
    # Non-AJAX fallback (if any)
    return redirect('course_list')


@login_required
def course_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    course = get_object_or_404(Course, pk=pk)
    if request.user.role == 'center' and not _center_manages_course(request.user.center, course):
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
        
    if request.method == 'POST':
        course.delete()
        messages.success(request, 'Course deleted successfully.')
        return redirect('course_list')
    return render(request, 'courses/course_confirm_delete.html', {'course': course})


@login_required
def course_restore(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
    course = get_object_or_404(Course.all_objects, pk=pk)
    if request.user.role == 'center' and not _center_manages_course(request.user.center, course):
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
    course.restore()
    messages.success(request, 'Course restored successfully.')
    return redirect('course_list')


@login_required
def course_permanent_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
    course = get_object_or_404(Course.all_objects, pk=pk)
    if request.user.role == 'center' and not _center_manages_course(request.user.center, course):
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")
    if request.method == 'POST':
        course.hard_delete()
        messages.success(request, 'Course permanently deleted successfully.')
    return redirect('course_list')
