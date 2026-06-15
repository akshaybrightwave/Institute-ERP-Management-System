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


@login_required
def fees_list(request):
    is_admin = request.user.role == 'admin'
    is_teacher = request.user.role == 'teacher'
    
    if not (is_admin or is_teacher):
        return HttpResponseForbidden("Access Denied: Admins or Teachers only.")
        
    tab = request.GET.get('tab', 'students')
    query = request.GET.get('q', '').strip()
    batch_id = request.GET.get('batch', '').strip()
    
    # Prepare data for Student summaries tab
    students_qs = StudentProfile.objects.select_related('batch__course', 'batch__teacher').annotate(
        paid_amount=Coalesce(Sum('feepayment__amount'), 0.00, output_field=DecimalField())
    )
    
    if is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        students_qs = students_qs.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:
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
        total_fee = student.batch.course.fees if (student.batch and student.batch.course) else 0.00
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
    
    # Prepare data for Payment Ledger tab (Admin only)
    payments_page_obj = None
    if is_admin:
        payments_qs = FeePayment.objects.select_related('student__batch__course').all().order_by('-payment_date', '-id')
        
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
        
    return render(request, 'fees/fees_list.html', {
        'students_page_obj': students_page_obj,
        'payments_page_obj': payments_page_obj,
        'batches': batches,
        'selected_batch': batch_id,
        'query': query,
        'tab': tab,
        'is_admin': is_admin
    })


@login_required
def payment_create(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")
        
    initial_student = request.GET.get('student')
    if request.method == 'POST':
        form = FeePaymentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee payment recorded successfully.")
            return redirect('fees_list')
    else:
        form = FeePaymentForm(initial={'student': initial_student})
        
    return render(request, 'fees/fee_form.html', {
        'form': form,
        'action': 'Add'
    })


@login_required
def payment_update(request, pk):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")
        
    payment = get_object_or_404(FeePayment, pk=pk)
    if request.method == 'POST':
        form = FeePaymentForm(request.POST, instance=payment)
        if form.is_valid():
            form.save()
            messages.success(request, "Fee payment updated successfully.")
            return redirect('fees_list')
    else:
        form = FeePaymentForm(instance=payment)
        
    return render(request, 'fees/fee_form.html', {
        'form': form,
        'action': 'Edit',
        'payment': payment
    })


@login_required
def payment_delete(request, pk):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")
        
    payment = get_object_or_404(FeePayment, pk=pk)
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Fee payment deleted successfully.")
        return redirect('fees_list')
        
    return render(request, 'fees/fee_confirm_delete.html', {
        'payment': payment
    })
