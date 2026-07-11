import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q

from .models import AdmitCard
from .forms import AdmitCardForm
from apps.students.models import StudentAdmission


def _handle_list_and_csv(request, is_center):
    qs = AdmitCard.objects.select_related('student', 'session', 'student__course', 'student__center').all()
    if is_center:
        qs = qs.filter(student__center=request.user.center)

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(student__student_name__icontains=query) |
            Q(student__enrollment_no__icontains=query) |
            Q(roll_number__icontains=query)
        )

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="admit_cards.csv"'
        writer = csv.writer(response)
        writer.writerow(['Enrollment No', 'Student Name', 'Course', 'Duration', 'Session', 'Institute'])
        for ac in qs:
            writer.writerow([
                ac.student.enrollment_no,
                ac.student.student_name,
                ac.student.course.name if ac.student.course else '',
                ac.student.course.duration if ac.student.course else '',
                ac.session.session_name,
                ac.student.center.name if ac.student.center else '',
            ])
        return response, True

    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs.order_by('-created_at', '-id'), per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return {
        'page_obj': page_obj,
        'query': query,
        'show_entries': show_entries,
    }, False


@login_required
def admit_card_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    is_student = request.user.role == 'student'

    if not (is_admin or is_center or is_teacher or is_student):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    if is_student:
        profile = getattr(request.user, 'studentprofile', None)
        qs = AdmitCard.objects.select_related('student', 'session', 'student__course', 'student__center').all()
        if profile:
            qs = qs.filter(Q(student__enrollment_no=request.user.username) | Q(student__email=profile.email))
        else:
            qs = qs.filter(student__enrollment_no=request.user.username)
        
        paginator = Paginator(qs.order_by('-created_at', '-id'), 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        
        return render(request, 'admit_card/admit_card_list.html', {
            'page_obj': page_obj,
            'is_student': True,
        })

    res = _handle_list_and_csv(request, is_center)
    if res[1]:
        return res[0]

    context = res[0]
    context.update({
        'is_admin': is_admin,
        'is_center': is_center,
        'is_teacher': is_teacher,
    })
    return render(request, 'admit_card/admit_card_list.html', context)


@login_required
def admit_card_create(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Only Admin or Center can access.")

    form = AdmitCardForm(user=request.user)
    selected_student_obj = None

    if request.method == 'POST':
        post_data = request.POST.copy()
        if is_center:
            post_data['center'] = request.user.center.id

        form = AdmitCardForm(post_data, user=request.user)
        if form.is_valid():
            admit_card = form.save(commit=False)
            admit_card.created_by = request.user
            admit_card.save()
            messages.success(request, 'Admit Card published successfully.')
            return redirect('admit_card_create')
        else:
            messages.error(request, 'Please correct the errors below.')
            student_id = request.POST.get('student')
            if student_id:
                try:
                    selected_student_obj = StudentAdmission.objects.get(id=student_id)
                except StudentAdmission.DoesNotExist:
                    pass

    res = _handle_list_and_csv(request, is_center)
    if res[1]:
        return res[0]

    context = res[0]
    context.update({
        'form': form,
        'is_admin': is_admin,
        'is_center': is_center,
        'selected_student_obj': selected_student_obj,
    })
    return render(request, 'admit_card/admit_card_create.html', context)


@login_required
def admit_card_view(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    is_student = request.user.role == 'student'

    if not (is_admin or is_center or is_teacher or is_student):
        return HttpResponseForbidden("Access Denied.")

    admit_card = get_object_or_404(
        AdmitCard.objects.select_related('student', 'session', 'student__course', 'student__center'),
        pk=pk
    )
    
    if is_student:
        profile = getattr(request.user, 'studentprofile', None)
        if not (admit_card.student.enrollment_no == request.user.username or (profile and profile.email and admit_card.student.email == profile.email)):
            return HttpResponseForbidden("Access Denied: You cannot view other students' admit cards.")
    elif is_center and admit_card.student.center != request.user.center:
        return HttpResponseForbidden("Access Denied: Student is not in your center.")

    return render(request, 'admit_card/admit_card_view.html', {
        'admit_card': admit_card,
    })


@login_required
def admit_card_delete(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")

    admit_card = get_object_or_404(AdmitCard, pk=pk)
    if is_center and admit_card.student.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You cannot delete admit cards of other centers.")

    admit_card.delete()
    messages.success(request, 'Admit Card deleted successfully.')
    return redirect('admit_card_list')


@login_required
def get_student_details(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'error': 'No student ID provided'}, status=400)
    try:
        student = StudentAdmission.objects.select_related('course').get(id=student_id)
        
        # Check permissions for center users
        if request.user.role == 'center' and student.center != request.user.center:
            return JsonResponse({'error': 'Unauthorized center'}, status=403)
            
        return JsonResponse({
            'course': student.course.name if student.course else '—',
            'duration': student.course.duration if student.course else '—',
        })
    except StudentAdmission.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)


@login_required
def student_admit_card_autocomplete(request):
    q = request.GET.get('q', '').strip()
    center_id = request.GET.get('center_id', '').strip()
    results = []
    
    qs = StudentAdmission.objects.filter(status='Approved')
    
    if request.user.role == 'center':
        qs = qs.filter(center=request.user.center)
    elif center_id:
        qs = qs.filter(center_id=center_id)
        
    if q:
        qs = qs.filter(
            Q(student_name__icontains=q) |
            Q(enrollment_no__icontains=q) |
            Q(whatsapp_no__icontains=q)
        )
        
    qs = qs.order_by('student_name')[:20]
    
    for s in qs:
        results.append({
            'id': s.id,
            'db_id': s.id,
            'text': f'{s.student_name} ({s.enrollment_no})',
            'name': s.student_name,
            'enrollment': s.enrollment_no,
            'mobile': s.whatsapp_no,
        })
    return JsonResponse({'results': results})

