from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from django.utils.http import url_has_allowed_host_and_scheme
from apps.accounts.views import admin_required
from apps.students.models import StudentAdmission, StudentProfile
from apps.batches.models import Batch
from apps.teachers.models import TeacherProfile
from .models import CenterPaymentSetting, FeePayment, StudentPaymentSetting
from .forms import CenterPaymentSettingForm, FeePaymentForm, StudentPaymentSettingForm
from .services import sync_center_payment_settings, sync_student_payment_settings
from decimal import Decimal


def _build_fee_emi_schedule(course_fee, paid_amount):
    course_fee = Decimal(str(course_fee or Decimal('0.00')))
    paid_amount = Decimal(str(paid_amount or Decimal('0.00')))
    if course_fee <= 0:
        return []

    installment_count = 4
    installment_amount = (course_fee / installment_count).quantize(Decimal('0.01'))
    remaining_paid = paid_amount
    rows = []

    for installment_no in range(1, installment_count + 1):
        amount = installment_amount if installment_no < installment_count else course_fee - (installment_amount * (installment_count - 1))
        if remaining_paid >= amount:
            status = 'Paid'
            paid_for_installment = amount
            remaining_paid -= amount
        elif remaining_paid > 0:
            status = 'Partially Paid'
            paid_for_installment = remaining_paid
            remaining_paid = Decimal('0.00')
        else:
            status = 'Pending'
            paid_for_installment = Decimal('0.00')

        rows.append({
            'installment_no': installment_no,
            'due_date': f'Month {installment_no}',
            'amount': amount,
            'paid_amount': paid_for_installment,
            'status': status,
        })

    return rows


def _get_student_admission(profile):
    if not profile:
        return None

    qs = StudentAdmission.objects.select_related('course', 'center', 'user')
    if profile.user_id:
        admission = qs.filter(user=profile.user).first()
        if admission:
            return admission

        admission = qs.filter(enrollment_no=profile.user.username).first()
        if admission:
            return admission

    if profile.email:
        admission = qs.filter(email=profile.email).first()
        if admission:
            return admission

    return qs.filter(student_name=profile.full_name).first()


def _center_student_q(center, prefix=''):
    if not center:
        return Q(**{f'{prefix}pk__in': []})

    admissions = StudentAdmission.objects.filter(center=center)
    admission_emails = admissions.exclude(email__isnull=True).exclude(email='').values_list('email', flat=True)
    admission_phones = admissions.exclude(whatsapp_no__isnull=True).exclude(whatsapp_no='').values_list('whatsapp_no', flat=True)

    return (
        Q(**{f'{prefix}batch__center': center}) |
        Q(**{f'{prefix}user_id__in': admissions.exclude(user__isnull=True).values_list('user_id', flat=True)}) |
        Q(**{f'{prefix}user__username__in': admissions.values_list('enrollment_no', flat=True)}) |
        Q(**{f'{prefix}email__in': admission_emails}) |
        Q(**{f'{prefix}phone__in': admission_phones}) |
        Q(**{f'{prefix}full_name__in': admissions.values_list('student_name', flat=True)})
    )


def _build_student_fee_summary(profile):
    admission = _get_student_admission(profile)
    course = None
    center = None
    batch_name = 'N/A'

    if admission:
        course = admission.course
        center = admission.center

    if profile and profile.batch:
        batch_name = profile.batch.name
        course = course or profile.batch.course
        center = center or profile.batch.center

    course_fee = profile.course_fee_at_admission if (profile and profile.course_fee_at_admission is not None) else (course.fees if course else Decimal('0.00'))
    paid_amount = FeePayment.objects.filter(student=profile).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    pending_balance = course_fee - paid_amount
    if pending_balance < Decimal('0.00'):
        pending_balance = Decimal('0.00')

    return {
        'admission': admission,
        'student_name': admission.student_name if admission else profile.full_name,
        'student_email': admission.email or profile.email if admission else profile.email,
        'enrollment_no': admission.enrollment_no if admission else '',
        'course_name': course.name if course else 'N/A',
        'batch_name': batch_name,
        'center_name': center.name if center else 'BRIGHTWAVE INSTITUTE',
        'total_fees': course_fee,
        'amount_paid': paid_amount,
        'pending_balance': pending_balance,
    }


def _payment_allowed_for_user(payment, user, summary=None):
    if user.role == 'admin':
        return True
    if user.role == 'student':
        return payment.student.user_id == user.id
    if user.role == 'center':
        summary = summary or _build_student_fee_summary(payment.student)
        admission = summary.get('admission')
        if admission and admission.center_id == getattr(user, 'center_id', None):
            return True
        return bool(payment.student.batch and payment.student.batch.center_id == getattr(user, 'center_id', None))
    return False


def _safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return None


@admin_required
def student_payment_setting(request):
    sync_student_payment_settings()

    if request.method == 'POST':
        if request.POST.get('action') == 'sync':
            created_count = sync_student_payment_settings()
            if created_count:
                messages.success(request, f"{created_count} student payment setting(s) synced successfully.")
            else:
                messages.info(request, "Student payment settings are already synced.")
            return redirect('student_payment_setting')

        settings_qs = StudentPaymentSetting.objects.filter(
            title__in=['Admission Fees', 'Re-Admission Fees', 'Exam Fees', 'Re-Exam Fees']
        ).only('id', 'title', 'amount', 'is_visible', 'sort_order').order_by('sort_order', 'title')
        forms = []
        is_valid = True
        for setting in settings_qs:
            form = StudentPaymentSettingForm(
                {
                    'amount': request.POST.get(f'amount_{setting.pk}', ''),
                    'is_visible': request.POST.get(f'is_visible_{setting.pk}') == 'on',
                },
                instance=setting,
            )
            forms.append((setting, form))
            if not form.is_valid():
                is_valid = False

        if is_valid:
            with transaction.atomic():
                StudentPaymentSetting.objects.bulk_update(
                    [form.save(commit=False) for _, form in forms],
                    ['amount', 'is_visible']
                )
            messages.success(request, "Student payment settings updated successfully.")
            return redirect('student_payment_setting')

        messages.error(request, "Please correct the errors below.")
        rows = forms
    else:
        rows = [
            (setting, StudentPaymentSettingForm(instance=setting))
            for setting in StudentPaymentSetting.objects.filter(
                title__in=['Admission Fees', 'Re-Admission Fees', 'Exam Fees', 'Re-Exam Fees']
            ).only('id', 'title', 'amount', 'is_visible', 'sort_order').order_by('sort_order', 'title')
        ]

    return render(request, 'fees/student_payment_setting.html', {
        'rows': rows,
    })


@admin_required
def center_payment_setting(request):
    sync_center_payment_settings()

    if request.method == 'POST':
        if request.POST.get('action') == 'sync':
            created_count = sync_center_payment_settings()
            if created_count:
                messages.success(request, f"{created_count} center payment setting(s) synced successfully.")
            else:
                messages.info(request, "Center payment settings are already synced.")
            return redirect('center_payment_setting')

        settings_qs = CenterPaymentSetting.objects.filter(
            title__in=['Admission Fees', 'Re-Admission Fees', 'Exam Fees', 'Re-Exam Fees']
        ).only('id', 'title', 'amount', 'is_visible', 'sort_order').order_by('sort_order', 'title')
        forms = []
        is_valid = True
        for setting in settings_qs:
            form = CenterPaymentSettingForm(
                {
                    'amount': request.POST.get(f'amount_{setting.pk}', ''),
                    'is_visible': request.POST.get(f'is_visible_{setting.pk}') == 'on',
                },
                instance=setting,
            )
            forms.append((setting, form))
            if not form.is_valid():
                is_valid = False

        if is_valid:
            with transaction.atomic():
                for _, form in forms:
                    form.save()
            messages.success(request, "Center payment settings updated successfully.")
            return redirect('center_payment_setting')

        messages.error(request, "Please correct the errors below.")
        rows = forms
    else:
        rows = [
            (setting, CenterPaymentSettingForm(instance=setting))
            for setting in CenterPaymentSetting.objects.filter(
                title__in=['Admission Fees', 'Re-Admission Fees', 'Exam Fees', 'Re-Exam Fees']
            ).only('id', 'title', 'amount', 'is_visible', 'sort_order').order_by('sort_order', 'title')
        ]

    return render(request, 'fees/center_payment_setting.html', {
        'rows': rows,
    })


@login_required
def fees_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    is_student = request.user.role == 'student'
    
    if not (is_admin or is_center or is_teacher or is_student):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    if request.method == 'POST' and (is_admin or is_center):
        action = request.POST.get('action')
        if action == 'delete_student_fee':
            student_id = request.POST.get('student_id')
            FeePayment.objects.filter(student_id=student_id).delete()
            messages.success(request, "All fee payments for the student have been deleted successfully.")
            return redirect(_safe_next_url(request) or 'fees_list')
        
    if is_student:
        from apps.students.models import StudentAdmission
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.forms import SetPasswordForm

        admission = StudentAdmission.objects.select_related('course', 'center').filter(user=request.user).first()
        if not admission:
            return HttpResponseForbidden("Access Denied: No student admission found.")

        active_tab = request.POST.get('active_tab') or request.GET.get('tab', 'fees')
        if active_tab == 'emis':
            active_tab = 'fees'
        if active_tab not in ['overview', 'fees', 'password', 'notifications']:
            active_tab = 'overview'

        password_form = SetPasswordForm(request.user)
        if request.method == 'POST' and request.POST.get('action') == 'change_password':
            active_tab = 'password'
            password_form = SetPasswordForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Password changed successfully.")
                return redirect(f"{request.path}?tab=password")
            messages.error(request, "Please correct the password fields below.")

        profile = getattr(request.user, 'studentprofile', None)
        if not profile:
            payments = FeePayment.objects.none()
            course_fee = admission.course.fees if admission.course else Decimal('0.00')
            paid_amount = Decimal('0.00')
            pending_amount = course_fee
            fee_status = 'PENDING'
        else:
            payments = FeePayment.objects.filter(student=profile).select_related('student__batch__course').order_by('-payment_date', '-id')
            course_fee = profile.course_fee_at_admission if profile.course_fee_at_admission is not None else Decimal('0.00')
            paid_amount = payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            paid_amount = Decimal(str(paid_amount))
            pending_amount = course_fee - paid_amount

            if paid_amount == 0:
                fee_status = 'PENDING'
            elif pending_amount <= 0:
                fee_status = 'PAID'
            else:
                fee_status = 'PARTIAL'

        if pending_amount < Decimal('0.00'):
            pending_amount = Decimal('0.00')

        query = request.GET.get('q', '').strip()
        if query and profile:
            payments = payments.filter(
                Q(reference_number__icontains=query) |
                Q(payment_method__icontains=query) |
                Q(remarks__icontains=query)
            )

        show_entries = request.GET.get('show', '10')
        try:
            per_page = int(show_entries)
        except ValueError:
            per_page = 10
        if per_page not in [10, 25, 50]:
            per_page = 10

        paginator = Paginator(payments, per_page)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, 'fees/student_fees_record.html', {
            'page_obj': page_obj,
            'fee_payments': page_obj,
            'admission': admission,
            'course_fee': course_fee,
            'paid_amount': paid_amount,
            'pending_amount': pending_amount,
            'fee_status': fee_status,
            'student_profile': profile,
            'password_form': password_form,
            'query': query,
            'show_entries': str(per_page),
            'notifications': [],
            'active_tab': active_tab,
        })
        
    tab = request.GET.get('tab', 'students')
    query = request.GET.get('q', '').strip()
    batch_id = request.GET.get('batch', '').strip()
    
    # Prepare data for Student summaries tab
    # Exclude soft-deleted payments via Q filter on the reverse FK annotation
    students_qs = StudentProfile.objects.select_related('batch__course', 'batch__teacher').annotate(
        paid_amount=Coalesce(
            Sum('feepayment__amount', filter=Q(feepayment__is_deleted=False)),
            Decimal('0.00'),
            output_field=DecimalField()
        )
    )

    if is_center:
        center = request.user.center
        students_qs = students_qs.filter(_center_student_q(center))
        batches = Batch.objects.filter(course__assignments__center=center, course__assignments__is_active=True)
    elif is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        students_qs = students_qs.filter(batch__teacher=teacher_profile)
        batches = Batch.objects.filter(teacher=teacher_profile)
    else:  # admin
        batches = Batch.objects.all()

    # Apply search/filter to student summaries
    if query:
        students_qs = students_qs.filter(
            Q(full_name__icontains=query) | Q(email__icontains=query) | Q(user__username__icontains=query)
        )
    if batch_id:
        students_qs = students_qs.filter(batch_id=batch_id)

    # Build student table list — use ONLY the locked course_fee_at_admission
    student_list = []
    for student in students_qs.order_by('full_name'):
        # Strictly use the locked historical fee; do NOT fall back to batch.course.fees
        total_fee = student.course_fee_at_admission if student.course_fee_at_admission is not None else Decimal('0.00')
        paid = student.paid_amount
        # Clamp pending to zero — overpayment is not shown as negative
        pending = max(total_fee - paid, Decimal('0.00'))

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
        payments_qs = FeePayment.objects.select_related('student__batch__course', 'student__batch__center').all().order_by('-payment_date', '-id')
        if is_center:
            payments_qs = payments_qs.filter(_center_student_q(request.user.center, prefix='student__'))
            
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

    # Calculate dashboard KPI metrics
    # FeePayment.objects.all() already excludes is_deleted=True via SoftDeleteManager.
    # However, for reverse-FK annotations on StudentProfile, we must use an explicit
    # Q filter so that deleted payments are excluded from per-student aggregations.
    metrics_students = StudentProfile.objects.select_related('batch__course')
    metrics_payments = FeePayment.objects.all()  # SoftDeleteManager already filters is_deleted=False

    if is_center:
        center = request.user.center
        metrics_students = metrics_students.filter(_center_student_q(center))
        metrics_payments = metrics_payments.filter(_center_student_q(center, prefix='student__'))
    elif is_teacher:
        teacher_profile = get_object_or_404(TeacherProfile, user=request.user)
        metrics_students = metrics_students.filter(batch__teacher=teacher_profile)
        metrics_payments = metrics_payments.filter(student__batch__teacher=teacher_profile)

    # Total collected fees (SoftDeleteManager excludes deleted records automatically)
    total_students_count = metrics_students.count()
    total_fee_collected = metrics_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Per-student annotation — explicitly exclude soft-deleted payments via Q filter
    students_annotated = metrics_students.annotate(
        paid_amount=Coalesce(
            Sum('feepayment__amount', filter=Q(feepayment__is_deleted=False)),
            Decimal('0.00'),
            output_field=DecimalField()
        )
    )

    total_course_fees = Decimal('0.00')
    paid_students_count = 0
    pending_students_count = 0

    for s in students_annotated:
        # Use ONLY the locked historical fee — no runtime fallback to batch.course.fees
        s_fee = s.course_fee_at_admission if s.course_fee_at_admission is not None else Decimal('0.00')
        total_course_fees += s_fee
        # Clamp: overpaying does not produce negative pending
        pending = max(s_fee - s.paid_amount, Decimal('0.00'))
        if pending <= Decimal('0.00'):
            paid_students_count += 1
        else:
            pending_students_count += 1

    total_pending_fees = max(total_course_fees - total_fee_collected, Decimal('0.00'))
    collection_percentage = (
        float(total_fee_collected) / float(total_course_fees) * 100
    ) if total_course_fees > Decimal('0.00') else 0.0
        
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
        payments_qs = payments_qs.filter(_center_student_q(request.user.center, prefix='student__'))
        
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
                student_profile = FeePaymentForm(user=request.user).fields['student'].queryset.get(pk=selected_student_id)
            else:
                student_profile = StudentProfile.objects.get(pk=selected_student_id)

            fee_summary = _build_student_fee_summary(student_profile)
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
        
    payment = get_object_or_404(FeePayment.objects.select_related('student__user', 'student__batch__course', 'student__batch__center'), pk=pk)
    next_url = _safe_next_url(request)
    payment_summary = _build_student_fee_summary(payment.student)
    
    # Check center isolation
    if is_center and not _payment_allowed_for_user(payment, request.user, payment_summary):
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
            student_profile = StudentProfile.objects.select_related('user', 'batch__course', 'batch__center').get(pk=selected_student_id)
            fee_summary = _build_student_fee_summary(student_profile)
            if is_center and not (
                (fee_summary['admission'] and fee_summary['admission'].center_id == getattr(request.user, 'center_id', None)) or
                (student_profile.batch and student_profile.batch.center_id == getattr(request.user, 'center_id', None))
            ):
                return HttpResponseForbidden("Access Denied: This student belongs to another center.")
        except StudentProfile.DoesNotExist:
            pass

    if request.method == 'POST':
        form = FeePaymentForm(
            request.POST,
            instance=payment,
            user=request.user,
            course_fee=fee_summary['total_fees'] if fee_summary else payment_summary['total_fees'],
        )
        if form.is_valid():
            form.save()
            messages.success(request, "Fee payment updated successfully.")
            return redirect(next_url or 'fees_list')
    else:
        form = FeePaymentForm(
            instance=payment,
            user=request.user,
            course_fee=fee_summary['total_fees'] if fee_summary else payment_summary['total_fees'],
        )
        
    return render(request, 'fees/fee_form.html', {
        'form': form,
        'action': 'Edit',
        'payment': payment,
        'fee_summary': fee_summary,
        'student_profile': student_profile,
        'next_url': next_url,
    })


@login_required
def payment_delete(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Admins or Centers only.")
        
    payment = get_object_or_404(FeePayment.objects.select_related('student__user', 'student__batch__course', 'student__batch__center'), pk=pk)
    next_url = _safe_next_url(request)
    payment_summary = _build_student_fee_summary(payment.student)
    
    # Check center isolation
    if is_center and not _payment_allowed_for_user(payment, request.user, payment_summary):
        return HttpResponseForbidden("Access Denied: This payment belongs to another center.")
            
    if request.method == 'POST':
        payment.delete()
        messages.success(request, "Fee payment deleted successfully.")
        return redirect(next_url or 'fees_list')
        
    return render(request, 'fees/fee_confirm_delete.html', {
        'payment': payment,
        'next_url': next_url,
    })


@login_required
def payment_receipt(request, pk):
    payment = get_object_or_404(FeePayment.objects.select_related('student__user', 'student__batch__course', 'student__batch__center'), pk=pk)
    user = request.user
    fee_summary = _build_student_fee_summary(payment.student)

    if not _payment_allowed_for_user(payment, user, fee_summary):
        return HttpResponseForbidden("Access Denied: You are not authorized to view this receipt.")
        
    receipt_number = f"RCPT-{payment.payment_date.year}-{payment.id:04d}"
    back_url = _safe_next_url(request)
    if not back_url and fee_summary['admission']:
        back_url = f"/student_profile/?student_id={fee_summary['admission'].pk}#fees"
    
    return render(request, 'fees/receipt.html', {
        'payment': payment,
        'receipt_number': receipt_number,
        'fee_summary': fee_summary,
        'course_fee': fee_summary['total_fees'],
        'remaining_balance': fee_summary['pending_balance'],
        'back_url': back_url,
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
        qs = StudentProfile.objects.select_related('batch__course', 'batch__center').filter(
            Q(full_name__icontains=q) |
            Q(phone__icontains=q) |
            Q(email__icontains=q)
        )
        if is_center and request.user.center:
            qs = qs.filter(_center_student_q(request.user.center))
        qs = qs.order_by('full_name')[:20]

        profiles = list(qs)

        # Try to enrich with StudentAdmission data (enrollment_no, photo, whatsapp_no)
        name_set = {p.full_name for p in profiles}
        adm_map = {}
        admission_qs = StudentAdmission.objects.filter(student_name__in=name_set)
        if is_center and request.user.center:
            admission_qs = admission_qs.filter(center=request.user.center)
        for adm in admission_qs:
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
        qs = StudentProfile.objects.select_related('batch__course', 'batch__center')
        if is_center and request.user.center:
            student = qs.filter(_center_student_q(request.user.center)).get(pk=student_id)
        else:
            student = qs.get(pk=student_id)
    except StudentProfile.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)

    fee_summary = _build_student_fee_summary(student)

    return JsonResponse({
        'student_id': student.pk,
        'student_name': student.full_name,
        'course_name': fee_summary['course_name'],
        'batch_name': fee_summary['batch_name'],
        'total_fee': str(fee_summary['total_fees']),
        'paid_amount': str(fee_summary['amount_paid']),
        'remaining_fee': str(fee_summary['pending_balance']),
        'has_due': fee_summary['pending_balance'] > Decimal('0.00'),
    })

