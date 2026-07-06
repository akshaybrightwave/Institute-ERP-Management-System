import csv
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.contrib import messages
from django.db.models import Q
from django.db import transaction
from django.core.paginator import Paginator

from .models import Certificate
from .forms import CertificateForm
from apps.students.models import StudentAdmission


def _handle_list_and_csv(request, is_center):
    qs = Certificate.objects.select_related('student', 'session', 'course', 'center').all()
    if is_center:
        qs = qs.filter(center=request.user.center)

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(student__student_name__icontains=query) |
            Q(student__enrollment_no__icontains=query) |
            Q(certificate_number__icontains=query) |
            Q(course__name__icontains=query)
        )
    qs = qs.order_by('-id')

    # Handle CSV Export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="certificates.csv"'
        writer = csv.writer(response)
        writer.writerow(['Enrollment No', 'Student Name', 'Course', 'Course Duration', 'Issue Date', 'Institute'])
        for cert in qs:
            writer.writerow([
                cert.student.enrollment_no,
                cert.student.student_name,
                cert.course.name if cert.course else '',
                cert.course_duration,
                cert.issue_date,
                cert.center.name if cert.center else ''
            ])
        return response

    return qs, query


@login_required
def certificate_create(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Only Admin or Center can generate certificates.")

    if request.method == 'POST':
        form = CertificateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    cert_obj = form.save(commit=False)
                    cert_obj.student = form.cleaned_data['student']
                    cert_obj.center = cert_obj.student.center
                    cert_obj.course = cert_obj.student.course
                    cert_obj.created_by = request.user
                    
                    # Generate unique certificate number
                    cert_obj.certificate_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
                    
                    cert_obj.save()
                messages.success(request, f"Certificate for {cert_obj.student.student_name} generated successfully!")
                return redirect('certificate_create')
            except Exception as e:
                messages.error(request, str(e))
        else:
            if not form.non_field_errors():
                messages.error(request, 'Please correct the errors below.')
    else:
        form = CertificateForm(user=request.user)

    qs, query = _handle_list_and_csv(request, is_center)
    if isinstance(qs, HttpResponse):
        return qs

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'certificates/certificate_create.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def certificate_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    # Read-only for teachers
    is_teacher = request.user.role == 'teacher'

    if not (is_admin or is_center or is_teacher):
        return HttpResponseForbidden("Access Denied.")

    qs, query = _handle_list_and_csv(request, is_center)
    if isinstance(qs, HttpResponse):
        return qs

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'certificates/certificate_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def certificate_detail(request, pk):
    cert = get_object_or_404(Certificate.objects.select_related('student', 'center', 'course', 'session'), pk=pk)

    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied: This certificate belongs to another center.")
    
    if request.user.role == 'student':
        # Verify if student's profile matches this admission
        if cert.student.email != request.user.email:
            return HttpResponseForbidden("Access Denied: You can only view your own certificates.")

    return render(request, 'certificates/certificate_detail.html', {
        'certificate': cert
    })


@login_required
def certificate_delete(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)

    if request.user.role == 'center' and cert.center != request.user.center:
        return HttpResponseForbidden("Access Denied.")
    if request.user.role not in ['admin', 'center']:
        return HttpResponseForbidden("Access Denied.")

    if request.method == 'POST':
        cert.delete()
        messages.success(request, "Certificate deleted successfully!")
        # If deleted from create page, redirect back there. Otherwise list page.
        referer = request.META.get('HTTP_REFERER', '')
        if 'create' in referer:
            return redirect('certificate_create')
        return redirect('certificate_list')

    return HttpResponseForbidden("Invalid request.")
