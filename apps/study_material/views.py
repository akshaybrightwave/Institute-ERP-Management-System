import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse, FileResponse, Http404
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from .models import StudyMaterial
from .forms import StudyMaterialForm
from apps.courses.models import Course


@login_required
def study_material_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    is_student = request.user.role == 'student'

    if not (is_admin or is_center or is_teacher or is_student):
        return HttpResponseForbidden("Access Denied.")

    if is_student:
        from apps.students.models import StudentAdmission
        admission = StudentAdmission.objects.select_related('center', 'course').filter(user=request.user).first()
        if not admission:
            return HttpResponseForbidden("Access Denied: Student record not found.")

        qs = StudyMaterial.objects.filter(
            center=admission.center,
            course=admission.course
        ).select_related('center', 'course', 'uploaded_by')

        q = request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(description__icontains=q)
            )

        qs = qs.order_by('-id')
        paginator = Paginator(qs, 10)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        return render(request, 'study_material/student_material_list.html', {
            'page_obj': page_obj,
            'query': q,
            'admission': admission,
        })

    form = StudyMaterialForm(user=request.user)

    if request.method == 'POST':
        if is_teacher:
            return HttpResponseForbidden("Access Denied: Teachers cannot upload materials.")
            
        form = StudyMaterialForm(request.POST, request.FILES, user=request.user)
        course_id = request.POST.get('course')
        if course_id:
            if is_center:
                form.fields['course'].queryset = Course.objects.filter(
                    id=course_id,
                    assignments__center=request.user.center,
                    assignments__is_active=True
                )
            else:
                admin_center_id = request.POST.get('center')
                if admin_center_id:
                    form.fields['course'].queryset = Course.objects.filter(
                        id=course_id,
                        assignments__center_id=admin_center_id,
                        assignments__is_active=True
                    )
                else:
                    form.fields['course'].queryset = Course.objects.filter(id=course_id)

        if form.is_valid():
            try:
                with transaction.atomic():
                    material = form.save(commit=False)
                    if is_center:
                        material.center = request.user.center
                    material.uploaded_by = request.user
                    material.save()
                messages.success(request, "Study Material uploaded successfully!")
                return redirect('study_material_list')
            except Exception as e:
                messages.error(request, f"Error saving study material: {str(e)}")
        else:
            messages.error(request, "Please correct the errors in the form.")

    # Fetch materials
    qs = StudyMaterial.objects.select_related('center', 'course', 'uploaded_by').all()
    if is_center:
        qs = qs.filter(center=request.user.center)

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(
            Q(title__icontains=q) |
            Q(course__name__icontains=q) |
            Q(description__icontains=q)
        )

    # Export to CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="study_materials.csv"'
        writer = csv.writer(response)
        writer.writerow(['Course', 'Title', 'File Type', 'Uploaded Date', 'Uploaded By'])
        for item in qs.order_by('-id'):
            writer.writerow([
                item.course.name,
                item.title,
                item.file_type,
                item.created_at.strftime('%Y-%m-%d'),
                item.uploaded_by.username if item.uploaded_by else 'System'
            ])
        return response

    # Ordering
    qs = qs.order_by('-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'study_material/study_material_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
        'is_admin': is_admin,
        'is_center': is_center,
        'is_teacher': is_teacher,
    })


@login_required
def study_material_edit(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")

    material = get_object_or_404(StudyMaterial, pk=pk)
    if is_center and material.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's data.")

    if request.method == 'POST':
        form = StudyMaterialForm(request.POST, request.FILES, instance=material, user=request.user)
        course_id = request.POST.get('course')
        if course_id:
            if is_center:
                form.fields['course'].queryset = Course.objects.filter(
                    id=course_id,
                    assignments__center=request.user.center,
                    assignments__is_active=True
                )
            else:
                admin_center_id = request.POST.get('center')
                if admin_center_id:
                    form.fields['course'].queryset = Course.objects.filter(
                        id=course_id,
                        assignments__center_id=admin_center_id,
                        assignments__is_active=True
                    )
                else:
                    form.fields['course'].queryset = Course.objects.filter(id=course_id)

        if form.is_valid():
            form.save()
            messages.success(request, "Study Material updated successfully!")
            return redirect('study_material_list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = StudyMaterialForm(instance=material, user=request.user)

    return render(request, 'study_material/study_material_edit.html', {
        'form': form,
        'material': material,
    })


@login_required
def study_material_delete(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")

    if request.method == 'POST':
        material = get_object_or_404(StudyMaterial, pk=pk)
        if is_center and material.center != request.user.center:
            return HttpResponseForbidden("Access Denied.")
        material.delete()
        messages.success(request, "Study Material deleted successfully (soft delete).")
        
    return redirect('study_material_list')


@login_required
def study_material_download(request, pk):
    material = get_object_or_404(StudyMaterial, pk=pk)
    
    user = request.user
    if user.role == 'center' and material.center != user.center:
        return HttpResponseForbidden("Access Denied.")
    elif user.role == 'student':
        from apps.students.models import StudentAdmission
        admission = StudentAdmission.objects.filter(user=user).first()
        if not admission or admission.center != material.center or admission.course != material.course:
            return HttpResponseForbidden("Access Denied: This material is not assigned to your course.")

    if not material.upload_file:
        raise Http404("No file uploaded for this study material.")

    return FileResponse(material.upload_file.open('rb'), as_attachment=True)


@login_required
def ajax_get_courses(request):
    center_id = request.GET.get('center_id')
    if not center_id:
        if request.user.role == 'center':
            if not request.user.center:
                return JsonResponse({'courses': []})
            courses = Course.objects.filter(
                assignments__center=request.user.center,
                assignments__is_active=True
            ).distinct().order_by('name')
        elif request.user.role in ('admin', 'teacher'):
            courses = Course.objects.all().order_by('name')
        else:
            return JsonResponse({'courses': []})
    else:
        courses = Course.objects.filter(
            assignments__center_id=center_id,
            assignments__is_active=True
        ).distinct().order_by('name')
    data = [{'id': c.id, 'name': c.name} for c in courses]
    return JsonResponse({'courses': data})
