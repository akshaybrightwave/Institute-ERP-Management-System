from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from .models import Subject, SubjectOrder
from .forms import SubjectForm
from apps.courses.models import Course


@login_required
def subject_list(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    form = SubjectForm(user=request.user)

    if request.method == 'POST':
        form = SubjectForm(request.POST, user=request.user)
        # Force populate the duration choices from the POST data so it passes form validation
        val = request.POST.get('duration_offset')
        if val:
            form.fields['duration_offset'].choices = [(val, val)]

        if form.is_valid():
            subject = form.save(commit=False)
            
            # Additional validation: duplicate check
            course = form.cleaned_data.get('course')
            code = form.cleaned_data.get('subject_code', '').strip()
            name = form.cleaned_data.get('name', '').strip()

            if Subject.objects.filter(course=course, subject_code__iexact=code).exists():
                form.add_error('subject_code', 'Subject with this code already exists for this course.')
            elif Subject.objects.filter(course=course, name__iexact=name).exists():
                form.add_error('name', 'Subject with this name already exists for this course.')
            else:
                subject.save()
                messages.success(request, 'Subject created successfully.')
                return redirect('subject_list')

    # Search & Filter
    query = request.GET.get('q', '').strip()
    if request.user.role == 'center':
        if not request.user.center:
            qs = Subject.objects.none()
            deleted_qs = Subject.all_objects.none()
        else:
            qs = Subject.objects.filter(course__center=request.user.center).select_related('course')
            deleted_qs = Subject.all_objects.filter(course__center=request.user.center, is_deleted=True).select_related('course')
    else:
        qs = Subject.objects.all().select_related('course')
        deleted_qs = Subject.all_objects.filter(is_deleted=True).select_related('course')

    if query:
        qs = qs.filter(name__icontains=query) | qs.filter(subject_code__icontains=query)
        deleted_qs = deleted_qs.filter(name__icontains=query) | deleted_qs.filter(subject_code__icontains=query)

    qs = qs.order_by('-id')
    deleted_subjects = deleted_qs.order_by('-deleted_at', '-id')

    # Pagination
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'subjects/subject_list.html', {
        'form': form,
        'page_obj': page_obj,
        'deleted_subjects': deleted_subjects,
        'query': query,
    })


@login_required
def subject_update(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    subject = get_object_or_404(Subject.all_objects, pk=pk)
    if request.user.role == 'center' and subject.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")

    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if request.method == 'POST':
            # Bind and validate
            form = SubjectForm(request.POST, instance=subject, user=request.user)
            val = request.POST.get('duration_offset')
            if val:
                form.fields['duration_offset'].choices = [(val, val)]

            if form.is_valid():
                form.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'errors': form.errors})

        # GET request: return details for modal population
        # Return course duration value and unit so JS can build duration dropdown correctly
        course_duration = subject.course.duration
        return JsonResponse({
            'course_id': subject.course.id,
            'course_duration': course_duration,
            'duration_offset': subject.duration_offset,
            'subject_code': subject.subject_code,
            'name': subject.name,
            'subject_type': subject.subject_type,
            'theory_max_marks': subject.theory_max_marks,
            'theory_min_marks': subject.theory_min_marks,
            'practical_max_marks': subject.practical_max_marks,
            'practical_min_marks': subject.practical_min_marks,
        })

    return redirect('subject_list')


@login_required
def subject_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    subject = get_object_or_404(Subject, pk=pk)
    if request.user.role == 'center' and subject.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")

    if request.method == 'POST':
        subject.delete()
        messages.success(request, 'Subject deleted successfully.')
    return redirect('subject_list')


@login_required
def subject_restore(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    subject = get_object_or_404(Subject.all_objects, pk=pk)
    if request.user.role == 'center' and subject.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")

    subject.restore()
    messages.success(request, 'Subject restored successfully.')
    return redirect('subject_list')


@login_required
def subject_permanent_delete(request, pk):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    subject = get_object_or_404(Subject.all_objects, pk=pk)
    if request.user.role == 'center' and subject.course.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's courses.")

    if request.method == 'POST':
        subject.hard_delete()
        messages.success(request, 'Subject permanently deleted successfully.')
    return redirect('subject_list')


@login_required
def get_course_details(request, course_id):
    """
    Helper API endpoint to get course details like duration so dynamic front-end selectors work
    """
    course = get_object_or_404(Course, id=course_id)
    return JsonResponse({
        'duration': course.duration
    })


@login_required
def arrange_subjects(request):
    if request.user.role not in ('admin', 'center'):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    # Get active courses for the dropdown
    if request.user.role == 'center':
        if not request.user.center:
            courses = Course.objects.none()
        else:
            courses = Course.objects.filter(center=request.user.center)
    else:
        courses = Course.objects.all()

    selected_course_id = request.GET.get('course_id') or request.POST.get('course_id')
    selected_course = None
    subjects = []

    if selected_course_id:
        # Validate course exists and user has permission
        if request.user.role == 'center':
            selected_course = get_object_or_404(Course, id=selected_course_id, center=request.user.center)
        else:
            selected_course = get_object_or_404(Course, id=selected_course_id)

        # Load active subjects for the selected course
        active_subjects = Subject.objects.filter(course=selected_course)

        # Get existing orders
        orders = {o.subject_id: o.order for o in SubjectOrder.objects.filter(course=selected_course)}

        # Sort subjects: those with existing sequence first (by order), then by id DESC
        subjects = list(active_subjects)
        subjects.sort(key=lambda s: (orders.get(s.id, 999999), -s.id))

    if request.method == 'POST':
        # Save sequence
        subject_ids = request.POST.getlist('subject_ids[]') or request.POST.getlist('subject_ids')
        
        # Handle fallback if serialized as a single comma-separated string
        if len(subject_ids) == 1 and ',' in subject_ids[0]:
            subject_ids = [sid.strip() for sid in subject_ids[0].split(',') if sid.strip()]

        # Validation: check course is selected
        if not selected_course:
            return JsonResponse({'success': False, 'message': 'Course is not selected.'}, status=400)
            
        # Validation: no subjects submitted
        if not subject_ids:
            return JsonResponse({'success': False, 'message': 'No subjects submitted.'}, status=400)
            
        # Validation: check if any subject ID is missing
        if any(not sid for sid in subject_ids):
            return JsonResponse({'success': False, 'message': 'Subject ID missing.'}, status=400)
            
        # Validation: duplicate subject detected
        if len(subject_ids) != len(set(subject_ids)):
            return JsonResponse({'success': False, 'message': 'Duplicate subject detected.'}, status=400)

        # Validate that all subject_ids belong to the selected course
        valid_subject_ids = set(map(str, active_subjects.values_list('id', flat=True)))
        for sid in subject_ids:
            if sid not in valid_subject_ids:
                return JsonResponse({'success': False, 'message': f'Subject ID {sid} does not belong to selected course.'}, status=400)

        # Update or create orders
        try:
            # Delete old orders for this course to start fresh
            SubjectOrder.objects.filter(course=selected_course).delete()
            
            # Save new orders
            objs = []
            for index, sid in enumerate(subject_ids):
                subj = active_subjects.get(id=int(sid))
                objs.append(SubjectOrder(course=selected_course, subject=subj, order=index + 1))
            SubjectOrder.objects.bulk_create(objs)
            
            messages.success(request, 'Subject arrangement saved successfully.')
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    # If it's AJAX GET request to load subjects list
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        subjects_data = []
        for s in subjects:
            subjects_data.append({
                'id': s.id,
                'name': s.name,
                'code': s.subject_code
            })
        return JsonResponse({'subjects': subjects_data})

    return render(request, 'subjects/arrange_subjects.html', {
        'courses': courses,
        'selected_course': selected_course,
        'subjects': subjects,
    })
