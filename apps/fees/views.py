from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from apps.students.models import StudentProfile
from apps.batches.models import Batch
from apps.teachers.models import TeacherProfile
from .models import FeePayment
from .forms import FeePaymentForm
from decimal import Decimal


@login_required
def fees_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    
    if not (is_admin or is_center or is_teacher):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")
        
    tab = request.GET.get('tab', 'students')
    query = request.GET.get('q', '').strip()
    batch_id = request.GET.get('batch', '').strip()
    
    # Prepare data for Student summaries tab
    students_qs = StudentProfile.objects.select_related('batch__course', 'batch__teacher').annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'), output_field=DecimalField())
    )
    
    if is_center:
        center = request.user.center
        students_qs = students_qs.filter(batch__center=center)
        batches = Batch.objects.filter(course__assignments__center=center, course__assignments__is_active=True)
    elif is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        students_qs = students_qs.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
    else: # admin
        batches = Batch.objects.all()
        
    # Apply search/filter to student summaries
    if query:
        students_qs = students_qs.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(user__username__icontains=query)
        )
    if batch_id:
        students_qs = students_qs.filter(batch_id=batch_id)
        
    # Calculate pending and status for each student
    student_list = []
    for student in students_qs.order_by('full_name'):
        total_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
        paid = student.paid_amount
        pending = total_fee - paid
        
        if paid == 0:
            status = 'PENDING'
        elif pending <= 0:
            status = 'PAID'
        else:
            status = 'PARTIAL'
            
        student_list.append({
            'student': student,
            'course_fee': total_fee,
            'paid_amount': paid,
            'pending_amount': pending,
            'status': status
        })
        
    # Pagination for student list
    paginator_students = Paginator(student_list, 15)
    page_students = request.GET.get('page_students', 1)
    students_page_obj = paginator_students.get_page(page_students)
    
    # Prepare data for Payment Ledger tab (Admin & Center only)
    payments_page_obj = None
    if is_admin or is_center:
        payments_qs = FeePayment.objects.select_related('student__batch__course').all().order_by('-payment_date', '-id')
        if is_center:
            payments_qs = payments_qs.filter(student__batch__center=request.user.center)
            
        # Search/Filter in payments
        if query:
            payments_qs = payments_qs.filter(
                Q(student__full_name__icontains=query) | Q(reference_number__icontains=query)
            )
        if batch_id:
            payments_qs = payments_qs.filter(student__batch_id=batch_id)
            
        paginator_payments = Paginator(payments_qs, 15)
        page_payments = request.GET.get('page_payments', 1)
        payments_page_obj = paginator_payments.get_page(page_payments)

    # Calculate dashboard metrics (restricted to logged-in center for center, global for admin)
    metrics_students = StudentProfile.objects.select_related('batch__course')
    metrics_payments = FeePayment.objects.all()
    
    if is_center:
        center = request.user.center
        metrics_students = metrics_students.filter(batch__center=center)
        metrics_payments = metrics_payments.filter(student__batch__center=center)
    elif is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        metrics_students = metrics_students.filter(batch__teacher=teacher_profile)
        metrics_payments = metrics_payments.filter(student__batch__teacher=teacher_profile)

    # Aggregations for dashboard
    total_students_count = metrics_students.count()
    total_fee_collected = metrics_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    students_annotated = metrics_students.annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), Decimal('0.00'), output_field=DecimalField())
    )
    
    total_course_fees = Decimal('0.00')
    paid_students_count = 0
    pending_students_count = 0
    
    for s in students_annotated:
        s_fee = s.batch.course.fees if (s.batch and s.batch.course) else Decimal('0.00')
        total_course_fees += s_fee
        if s.paid_amount >= s_fee:
            paid_students_count += 1
        else:
            pending_students_count += 1
            
    total_pending_fees = total_course_fees - total_fee_collected
    if total_pending_fees < Decimal('0.00'):
        total_pending_fees = Decimal('0.00')
        
    collection_percentage = (float(total_fee_collected) / float(total_course_fees) * 100) if total_course_fees > Decimal('0.00') else 0.0
        
    return render(request, 'fees/fees_list.html', {
        'students_page_obj': students_page_obj,
        'payments_page_obj': payments_page_obj,
        'batches': batches,
        'selected_batch': batch_id,
        'query': query,
        'tab': tab,
        'is_admin': is_admin,
        'is_center': is_center,
        'is_teacher': is_teacher,
        
        # Metrics
        'total_students_count': total_students_count,
        'total_fee_collected': total_fee_collected,
        'total_pending_fees': total_pending_fees,
        'collection_percentage': round(collection_percentage, 1),
        'paid_students_count': paid_students_count,
        'pending_students_count': pending_students_count,
    })


@login_required
def search_fee_payment(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Admins or Centers only.")
        
    query = request.GET.get('q', '').strip()
    show_entries = request.GET.get('show', '10')
    
    try:
        show = int(show_entries)
    except ValueError:
        show = 10
        
    payments_qs = FeePayment.objects.select_related('student').all().order_by('-payment_date', '-id')
    
    if is_center:
        payments_qs = payments_qs.filter(student__batch__center=request.user.center)
        
    if query:
        q_filter = Q(id__icontains=query) | Q(reference_number__icontains=query) | Q(student__full_name__icontains=query) | Q(student__phone__icontains=query)
        
        # Search via enrollment number mapped by name
        from apps.students.models import StudentAdmission
        matching_admissions = StudentAdmission.objects.filter(enrollment_no__icontains=query).values_list('student_name', flat=True)
        if matching_admissions:
            q_filter |= Q(student__full_name__in=matching_admissions)
            
        payments_qs = payments_qs.filter(q_filter)
        
    paginator = Paginator(payments_qs, show)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Enrich the current page with Enrollment No
    from apps.students.models import StudentAdmission
    names_on_page = [p.student.full_name for p in page_obj]
    adm_map = {
        adm.student_name: adm.enrollment_no
        for adm in StudentAdmission.objects.filter(student_name__in=names_on_page)
    }
    
    for payment in page_obj:
        payment.enrollment_no = adm_map.get(payment.student.full_name, "—")
        
    return render(request, 'fees/search_fee_payment.html', {
        'page_obj': page_obj,
        'query': query,
        'show_entries': show_entries,
    })

@login_required
def payment_create(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Admins or Centers only.")
        
    selected_student_id = None
    if request.method == 'POST':
        selected_student_id = request.POST.get('student')
    else:
        selected_student_id = request.GET.get('student')
        
    student_profile = None
    fee_summary = None
    if selected_student_id:
        try:
            if is_center:
                student_profile = StudentProfile.objects.get(pk=selected_student_id, batch__center=request.user.center)
            else:
                student_profile = StudentProfile.objects.get(pk=selected_student_id)
                
            total_fee = student_profile.batch.course.fees if (student_profile.batch and student_profile.batch.course) else Decimal('0.00')
            paid_amount = FeePayment.objects.filter(student=student_profile).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            pending_balance = total_fee - paid_amount
            fee_summary = {
                'student_name': student_profile.full_name,
                'course_name': student_profile.batch.course.name if (student_profile.batch and student_profile.batch.course) else 'N/A',
                'batch_name': student_profile.batch.name if student_profile.batch else 'N/A',
                'total_fees': total_fee,
                'amount_paid': paid_amount,
                'pending_balance': pending_balance
            }
        except StudentProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = FeePaymentForm(request.POST, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee payment recorded successfully.")
            return redirect('fees_list')
    else:
        form = FeePaymentForm(initial={'student': selected_student_id}, user=request.user)
        
    return render(request, 'fees/fee_form.html', {
        'form': form,
        'action': 'Add',
        'fee_summary': fee_summary,
        'student_profile': student_profile
    })


@login_required
def payment_update(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Admins or Centers only.")
        
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check center isolation
    if is_center:
        if not payment.student.batch or not payment.student.batch.course or payment.student.batch.center != request.user.center:
            return HttpResponseForbidden("Access Denied: This payment belongs to another center.")
            
    selected_student_id = None
    if request.method == 'POST':
        selected_student_id = request.POST.get('student')
    else:
        selected_student_id = request.GET.get('student') or payment.student_id
        
    student_profile = None
    fee_summary = None
    if selected_student_id:
        try:
            if is_center:
                student_profile = StudentProfile.objects.get(pk=selected_student_id, batch__center=request.user.center)
            else:
                student_profile = StudentProfile.objects.get(pk=selected_student_id)
                
            total_fee = student_profile.batch.course.fees if (student_profile.batch and student_profile.batch.course) else Decimal('0.00')
            paid_amount = FeePayment.objects.filter(student=student_profile).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            pending_balance = total_fee - paid_amount
            fee_summary = {
                'student_name': student_profile.full_name,
                'course_name': student_profile.batch.course.name if (student_profile.batch and student_profile.batch.course) else 'N/A',
                'batch_name': student_profile.batch.name if student_profile.batch else 'N/A',
                'total_fees': total_fee,
                'amount_paid': paid_amount,
                'pending_balance': pending_balance
            }
        except StudentProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = FeePaymentForm(request.POST, instance=payment, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee payment updated successfully.")
            return redirect('fees_list')
    else:
        form = FeePaymentForm(instance=payment, user=request.user)
        
    return render(request, 'fees/fee_form.html', {
        'form': form,
        'action': 'Edit',
        'payment': payment,
        'fee_summary': fee_summary,
        'student_profile': student_profile
    })


@login_required
def payment_delete(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Admins or Centers only.")
        
    payment = get_object_or_404(FeePayment, pk=pk)
    
    # Check center isolation
    if is_center:
        if not payment.student.batch or not payment.student.batch.course or payment.student.batch.center != request.user.center:
            return HttpResponseForbidden("Access Denied: This payment belongs to another center.")
            
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Fee payment deleted successfully.")
        return redirect('fees_list')
        
    return render(request, 'fees/fee_confirm_delete.html', {
        'payment': payment
    })


@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(FeePayment, pk=pk)
    user = request.user
    
    is_authorized = False
    if user.role == 'admin':
        is_authorized = True
    elif user.role == 'center':
        if user.center and payment.student.batch and payment.student.batch.center == user.center:
            is_authorized = True
    elif user.role == 'student':
        if payment.student.user == user:
            is_authorized = True
            
    if not is_authorized:
        return HttpResponseForbidden("Access Denied: You are not authorized to view this receipt.")
        
    student = payment.student
    course_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
    
    # Sum of all payments for this student
    total_paid = FeePayment.objects.filter(student=student).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    remaining_balance = course_fee - total_paid
    if remaining_balance < Decimal('0.00'):
        remaining_balance = Decimal('0.00')
        
    receipt_number = f"RCPT-{payment.payment_date.year}-{payment.id:04d}"
    
    return render(request, 'fees/receipt.html', {
        'payment': payment,
        'receipt_number': receipt_number,
        'course_fee': course_fee,
        'remaining_balance': remaining_balance,
        'is_admin': user.role == 'admin',
        'is_center': user.role == 'center',
    })


@login_required
def student_fee_autocomplete(request):
    """Return JSON list of StudentProfile records for Select2, enriched with StudentAdmission data when available."""
    from django.http import JsonResponse
    from django.db.models import Q
    from apps.students.models import StudentAdmission

    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    if not (is_admin or is_center):
        return JsonResponse({'results': []})

    q = request.GET.get('q', '').strip()
    results = []
    if q:
        # Primary search: StudentProfile (this is what FeePayment FK points to)
        qs = StudentProfile.objects.select_related('batch__course').filter(
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
        if is_center and request.user.center:
            qs = qs.filter(batch__center=request.user.center)
        qs = qs.order_by('full_name')[:20]

        profiles = list(qs)

        # Try to enrich with StudentAdmission data (enrollment_no, photo, whatsapp_no)
        name_set = {p.full_name for p in profiles}
        adm_map = {}
        for adm in StudentAdmission.objects.filter(student_name__in=name_set):
            adm_map[adm.student_name] = adm

        for sp in profiles:
            adm = adm_map.get(sp.full_name)
            if adm:
                photo_url = adm.photo.url if adm.photo else ''
                enrollment = adm.enrollment_no
                mobile = adm.whatsapp_no
            else:
                photo_url = sp.profile_picture.url if sp.profile_picture else ''
                enrollment = ''
                mobile = sp.phone or ''

            results.append({
                'id': sp.pk,
                'text': f'{sp.full_name} ({enrollment or mobile or sp.email})',
                'name': sp.full_name,
                'enrollment': enrollment,
                'phone': mobile,
                'photo': photo_url,
            })
    return JsonResponse({'results': results})




@login_required
def student_fee_summary_ajax(request):
    """Return fee summary JSON for a given StudentProfile pk — used by Collect Fee page AJAX."""
    from django.http import JsonResponse

    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    if not (is_admin or is_center):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    student_id = request.GET.get('student_id', '').strip()
    if not student_id:
        return JsonResponse({'error': 'No student_id provided'}, status=400)

    try:
        qs = StudentProfile.objects.select_related('batch__course')
        if is_center and request.user.center:
            student = qs.get(pk=student_id, batch__center=request.user.center)
        else:
            student = qs.get(pk=student_id)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

    total_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')
    paid_amount = FeePayment.objects.filter(student=student).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    remaining = total_fee - paid_amount
    if remaining < Decimal('0.00'):
        remaining = Decimal('0.00')

    return JsonResponse({
        'student_id': student.pk,
        'student_name': student.full_name,
        'course_name': student.batch.course.name if (student.batch and student.batch.course) else 'N/A',
        'batch_name': student.batch.name if student.batch else 'N/A',
        'total_fee': str(total_fee),
        'paid_amount': str(paid_amount),
        'remaining_fee': str(remaining),
        'has_due': remaining > Decimal('0.00'),
    })

