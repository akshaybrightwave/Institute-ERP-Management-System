from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import datetime
import json
from django.utils import timezone

from .models import Inquiry, Lead, CallLog, FollowUp, LeadImport, LeadNote, LeadActivity, ImportErrorLog, CounselingSession, VisitSheet, AdmissionSheet
from .forms import InquiryForm, LeadForm, CallLogForm, FollowUpForm, CounselingSessionForm, CounselorFollowUpForm, CounselorLeadStatusForm, VisitSheetForm, AdmissionSheetForm
from .decorators import telecaller_required, counselor_required

@login_required
@telecaller_required
def management_dashboard(request):
    if request.user.role == 'admin':
        return redirect('management_super_admin_dashboard')
        
    today = datetime.date.today()
    
    # Base Querysets with Data Isolation (telecaller sees own data)
    inquiries_qs = Inquiry.objects.filter(created_by=request.user)
    leads_qs = Lead.objects.filter(assigned_telecaller=request.user)
    calls_qs = CallLog.objects.filter(created_by=request.user)
    followups_qs = FollowUp.objects.filter(created_by=request.user)

    # Statistics Calculation (9 metrics)
    total_leads = leads_qs.count()
    assigned_leads = leads_qs.filter(assigned_telecaller__isnull=False).count()
    contacted_leads = leads_qs.filter(status='Contacted').count()
    interested_leads = leads_qs.filter(status='Interested').count()
    qualified_leads = leads_qs.filter(status='Qualified').count()
    rejected_leads = leads_qs.filter(status='Rejected').count()
    today_calls = calls_qs.filter(call_date__date=today).count()
    pending_followups = followups_qs.filter(status='Pending').count()
    overdue_followups = followups_qs.filter(status='Pending', followup_date__lt=today).count()

    # Call Outcomes
    call_outcomes = {
        'accepted': inquiries_qs.filter(call_status='ACCEPTED').count(),
        'busy': inquiries_qs.filter(call_status='BUSY').count(),
        'call_back': inquiries_qs.filter(call_status='CALL_BACK').count(),
        'interested': inquiries_qs.filter(call_status='INTERESTED').count(),
        'not_interested': inquiries_qs.filter(call_status='NOT_INTERESTED').count(),
    }

    # Tables
    recent_leads = leads_qs.order_by('-created_at')[:5]
    recent_activities = LeadActivity.objects.filter(lead__assigned_telecaller=request.user).order_by('-created_at')[:5]
    today_followups_list = followups_qs.filter(status='Pending', followup_date=today).order_by('followup_date')[:5]
    overdue_followups_list = followups_qs.filter(status='Pending', followup_date__lt=today).order_by('followup_date')[:5]

    context = {
        'total_leads': total_leads,
        'assigned_leads': assigned_leads,
        'contacted_leads': contacted_leads,
        'interested_leads': interested_leads,
        'qualified_leads': qualified_leads,
        'rejected_leads': rejected_leads,
        'today_calls': today_calls,
        'pending_followups': pending_followups,
        'overdue_followups': overdue_followups,
        'call_outcomes': call_outcomes,
        'recent_leads': recent_leads,
        'recent_activities': recent_activities,
        'today_followups_list': today_followups_list,
        'overdue_followups_list': overdue_followups_list,
    }
    return render(request, 'management/dashboard.html', context)


@login_required
def management_super_admin_dashboard(request):
    if request.user.role != 'admin':
        if request.user.role == 'telecaller':
            return redirect('management_dashboard')
        return HttpResponseForbidden("Access Denied: Admin access only.")

    today = datetime.date.today()

    # Global statistics (9 metrics)
    total_leads = Lead.objects.count()
    assigned_leads = Lead.objects.filter(assigned_telecaller__isnull=False).count()
    contacted_leads = Lead.objects.filter(status='Contacted').count()
    interested_leads = Lead.objects.filter(status='Interested').count()
    qualified_leads = Lead.objects.filter(status='Qualified').count()
    rejected_leads = Lead.objects.filter(status='Rejected').count()
    today_calls = CallLog.objects.filter(call_date__date=today).count()
    pending_followups = FollowUp.objects.filter(status='Pending').count()
    overdue_followups = FollowUp.objects.filter(status='Pending', followup_date__lt=today).count()

    # Call Outcomes
    call_outcomes = {
        'accepted': Inquiry.objects.filter(call_status='ACCEPTED').count(),
        'busy': Inquiry.objects.filter(call_status='BUSY').count(),
        'call_back': Inquiry.objects.filter(call_status='CALL_BACK').count(),
        'interested': Inquiry.objects.filter(call_status='INTERESTED').count(),
        'not_interested': Inquiry.objects.filter(call_status='NOT_INTERESTED').count(),
    }

    # Admission Metrics
    admission_metrics = {
        'total': AdmissionSheet.objects.count(),
        'confirmed': AdmissionSheet.objects.filter(admission_status='CONFIRMED').count(),
        'pending_payment': AdmissionSheet.objects.filter(admission_status='PENDING_PAYMENT').count(),
        'cancelled': AdmissionSheet.objects.filter(admission_status='CANCELLED').count(),
    }

    # Tables
    recent_leads = Lead.objects.order_by('-created_at')[:5]
    recent_activities = LeadActivity.objects.all().order_by('-created_at')[:5]
    today_followups_list = FollowUp.objects.filter(status='Pending', followup_date=today).order_by('followup_date')[:5]
    overdue_followups_list = FollowUp.objects.filter(status='Pending', followup_date__lt=today).order_by('followup_date')[:5]

    context = {
        'total_leads': total_leads,
        'assigned_leads': assigned_leads,
        'contacted_leads': contacted_leads,
        'interested_leads': interested_leads,
        'qualified_leads': qualified_leads,
        'rejected_leads': rejected_leads,
        'today_calls': today_calls,
        'pending_followups': pending_followups,
        'overdue_followups': overdue_followups,
        'call_outcomes': call_outcomes,
        'admission_metrics': admission_metrics,
        'recent_leads': recent_leads,
        'recent_activities': recent_activities,
        'today_followups_list': today_followups_list,
        'overdue_followups_list': overdue_followups_list,
    }
    return render(request, 'management/super_admin_dashboard.html', context)


# ==================================================
# INQUIRY CRUD
# ==================================================

@login_required
@telecaller_required
def inquiry_list(request):
    if request.user.role == 'admin':
        inquiries = Inquiry.objects.all()
    else:
        inquiries = Inquiry.objects.filter(created_by=request.user)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        inquiries = inquiries.filter(
            Q(full_name__icontains=q) | Q(mobile_number__icontains=q) | Q(city__icontains=q)
        )

    # Filters
    status = request.GET.get('status', '').strip()
    if status:
        inquiries = inquiries.filter(status=status)

    source = request.GET.get('source', '').strip()
    if source:
        inquiries = inquiries.filter(source=source)

    call_status = request.GET.get('call_status', '').strip()
    if call_status:
        inquiries = inquiries.filter(call_status=call_status)

    paginator = Paginator(inquiries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/inquiry_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'source': source,
        'call_status': call_status,
        'status_choices': Inquiry.STATUS_CHOICES,
        'source_choices': Inquiry.SOURCE_CHOICES,
        'call_status_choices': Inquiry.CALL_STATUS_CHOICES,
    })


@login_required
@telecaller_required
def inquiry_add(request):
    if request.method == 'POST':
        form = InquiryForm(request.POST)
        if form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.created_by = request.user
            inquiry.save()
            messages.success(request, f"Inquiry for {inquiry.full_name} created successfully.")
            return redirect('inquiry_list')
    else:
        form = InquiryForm()
    return render(request, 'management/inquiry_form.html', {'form': form, 'title': 'Add Inquiry'})


@login_required
@telecaller_required
def inquiry_detail(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and inquiry.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")
        
    return render(request, 'management/inquiry_detail.html', {'inquiry': inquiry})


@login_required
@telecaller_required
def inquiry_edit(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and inquiry.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    if request.method == 'POST':
        form = InquiryForm(request.POST, instance=inquiry)
        if form.is_valid():
            form.save()
            messages.success(request, f"Inquiry for {inquiry.full_name} updated successfully.")
            return redirect('inquiry_detail', pk=inquiry.pk)
    else:
        form = InquiryForm(instance=inquiry)
    return render(request, 'management/inquiry_form.html', {'form': form, 'inquiry': inquiry, 'title': 'Edit Inquiry'})


@login_required
@telecaller_required
def inquiry_delete(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and inquiry.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    if request.method == 'POST':
        name = inquiry.full_name
        inquiry.delete()
        messages.success(request, f"Inquiry for {name} deleted successfully.")
        return redirect('inquiry_list')
    return render(request, 'management/inquiry_confirm_delete.html', {'inquiry': inquiry})


@login_required
@telecaller_required
def inquiry_convert(request, pk):
    inquiry = get_object_or_404(Inquiry, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and inquiry.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    # Rule: Prevent duplicate Lead creation.
    if hasattr(inquiry, 'lead'):
        messages.warning(request, "This inquiry has already been converted to a Lead.")
        return redirect('lead_detail', pk=inquiry.lead.pk)

    if request.method == 'POST':
        # Create Lead
        lead = Lead.objects.create(
            inquiry=inquiry,
            assigned_telecaller=request.user,
            status='New',
            priority='Medium',
            assigned_by=request.user,
            assigned_at=timezone.now()
        )
        # Auto-update Inquiry status to Qualified
        inquiry.status = 'Qualified'
        inquiry.save()

        # Log lead activities
        log_lead_activity(lead, 'LEAD_CREATED', f"Lead created from inquiry conversion by {request.user.username}.", request.user)
        log_lead_activity(lead, 'ASSIGNED', f"Lead auto-assigned to {request.user.username} upon conversion.", request.user)

        messages.success(request, f"Inquiry for {inquiry.full_name} converted to Lead successfully.")
        return redirect('lead_detail', pk=lead.pk)

    return render(request, 'management/inquiry_convert.html', {'inquiry': inquiry})


@login_required
@telecaller_required
def update_call_status(request, pk):
    """AJAX endpoint to update call status inline from Inquiry Directory."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    inquiry = get_object_or_404(Inquiry, pk=pk)

    # Access control: Tele Caller can update own inquiries, Super Admin can update any
    if request.user.role != 'admin' and inquiry.created_by != request.user:
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)

    try:
        data = json.loads(request.body)
        new_status = data.get('call_status', '').strip()
    except (json.JSONDecodeError, AttributeError):
        return JsonResponse({'success': False, 'message': 'Invalid data.'}, status=400)

    valid_statuses = [choice[0] for choice in Inquiry.CALL_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'success': False, 'message': f'Invalid call status: {new_status}'}, status=400)

    inquiry.call_status = new_status
    inquiry.save(update_fields=['call_status', 'updated_at'])

    return JsonResponse({
        'success': True,
        'message': 'Call status updated successfully.',
        'call_status': new_status,
        'call_status_display': dict(Inquiry.CALL_STATUS_CHOICES).get(new_status, new_status),
    })


# ==================================================
# LEAD CRUD
# ==================================================

@login_required
@telecaller_required
def lead_list(request):
    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_telecaller=request.user)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        leads = leads.filter(
            Q(inquiry__full_name__icontains=q) | Q(inquiry__mobile_number__icontains=q)
        )

    # Filters
    status = request.GET.get('status', '').strip()
    if status:
        leads = leads.filter(status=status)

    priority = request.GET.get('priority', '').strip()
    if priority:
        leads = leads.filter(priority=priority)

    paginator = Paginator(leads, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/lead_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'priority': priority,
        'status_choices': Lead.STATUS_CHOICES,
        'priority_choices': Lead.PRIORITY_CHOICES,
    })


@login_required
@telecaller_required
def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    call_logs = lead.call_logs.all().order_by('-call_date')
    followups = lead.followups.all().order_by('-followup_date')

    # Check admission sheet
    try:
        admission = lead.admission_sheet
    except AdmissionSheet.DoesNotExist:
        admission = None

    return render(request, 'management/lead_detail.html', {
        'lead': lead,
        'call_logs': call_logs,
        'followups': followups,
        'admission': admission,
    })


@login_required
@telecaller_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    if request.method == 'POST':
        old_status = lead.status
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            updated_lead = form.save()
            if old_status != updated_lead.status:
                log_lead_activity(updated_lead, 'STATUS_CHANGED', f"Status updated from {old_status} to {updated_lead.status}.", request.user)
            messages.success(request, f"Lead for {lead.inquiry.full_name} updated successfully.")
            return redirect('lead_detail', pk=lead.pk)
    else:
        form = LeadForm(instance=lead)
    return render(request, 'management/lead_form.html', {'form': form, 'lead': lead})


# ==================================================
# CALL LOGS
# ==================================================

@login_required
@telecaller_required
def call_log_list(request):
    if request.user.role == 'admin':
        call_logs = CallLog.objects.all()
    else:
        call_logs = CallLog.objects.filter(created_by=request.user)

    lead_id = request.GET.get('lead_id', '').strip()
    if lead_id:
        call_logs = call_logs.filter(lead_id=lead_id)

    date_str = request.GET.get('date', '').strip()
    if date_str:
        try:
            date_val = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            call_logs = call_logs.filter(call_date__date=date_val)
        except ValueError:
            pass

    paginator = Paginator(call_logs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/calllog_list.html', {
        'page_obj': page_obj,
        'lead_id': lead_id,
        'date_str': date_str,
    })


@login_required
@telecaller_required
def call_log_add(request):
    lead_id = request.GET.get('lead_id', '')
    lead = None
    if lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
        if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

    if request.method == 'POST':
        form = CallLogForm(request.POST)
        selected_lead_id = request.POST.get('lead')
        selected_lead = get_object_or_404(Lead, pk=selected_lead_id)
        
        if request.user.role != 'admin' and selected_lead.assigned_telecaller != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

        if form.is_valid():
            log = form.save(commit=False)
            log.lead = selected_lead
            log.created_by = request.user
            log.save()
            # Log activity
            log_lead_activity(selected_lead, 'CALL_LOG_ADDED', f"Call log added: Status '{log.call_status}', Duration {log.call_duration}s.", request.user)
            messages.success(request, f"Call log saved successfully for {selected_lead.inquiry.full_name}.")
            return redirect('lead_detail', pk=selected_lead.pk)
    else:
        form = CallLogForm()

    # Get available leads for selection
    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_telecaller=request.user)

    return render(request, 'management/calllog_form.html', {
        'form': form,
        'leads': leads,
        'selected_lead': lead,
    })


# ==================================================
# FOLLOW UPS
# ==================================================

@login_required
@telecaller_required
def followup_list(request):
    if request.user.role == 'admin':
        followups = FollowUp.objects.all()
    else:
        followups = FollowUp.objects.filter(created_by=request.user)

    status = request.GET.get('status', '').strip()
    if status:
        followups = followups.filter(status=status)

    paginator = Paginator(followups, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/followup_list.html', {
        'page_obj': page_obj,
        'status': status,
    })


@login_required
@telecaller_required
def followup_add(request):
    lead_id = request.GET.get('lead_id', '')
    lead = None
    if lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
        if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

    if request.method == 'POST':
        form = FollowUpForm(request.POST)
        selected_lead_id = request.POST.get('lead')
        selected_lead = get_object_or_404(Lead, pk=selected_lead_id)

        if request.user.role != 'admin' and selected_lead.assigned_telecaller != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

        if form.is_valid():
            followup = form.save(commit=False)
            followup.lead = selected_lead
            followup.created_by = request.user
            followup.save()
            
            # Update Lead next follow up date
            selected_lead.next_followup_date = followup.followup_date
            selected_lead.save()

            # Log activity
            log_lead_activity(selected_lead, 'FOLLOWUP_CREATED', f"Follow-up scheduled for {followup.followup_date}.", request.user)

            messages.success(request, f"Follow-up scheduled successfully for {selected_lead.inquiry.full_name}.")
            return redirect('lead_detail', pk=selected_lead.pk)
    else:
        form = FollowUpForm()

    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_telecaller=request.user)

    return render(request, 'management/followup_form.html', {
        'form': form,
        'leads': leads,
        'selected_lead': lead,
        'title': 'Schedule Follow-Up',
    })


@login_required
@telecaller_required
def followup_edit(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role != 'admin' and followup.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    if request.method == 'POST':
        form = FollowUpForm(request.POST, instance=followup)
        if form.is_valid():
            form.save()
            
            # Sync next followup date on the lead if updated
            lead = followup.lead
            if followup.next_followup_date:
                lead.next_followup_date = followup.next_followup_date
            lead.save()

            messages.success(request, "Follow-up updated successfully.")
            return redirect('lead_detail', pk=followup.lead.pk)
    else:
        form = FollowUpForm(instance=followup)
    return render(request, 'management/followup_form.html', {
        'form': form,
        'followup': followup,
        'selected_lead': followup.lead,
        'title': 'Edit Follow-Up',
    })


@login_required
@telecaller_required
def followup_complete(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role != 'admin' and followup.created_by != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    followup.status = 'Completed'
    followup.save()
    # Log activity
    log_lead_activity(followup.lead, 'FOLLOWUP_COMPLETED', f"Follow-up scheduled on {followup.followup_date} completed.", request.user)
    messages.success(request, "Follow-up marked as Completed.")
    return redirect('lead_detail', pk=followup.lead.pk)


def map_header(raw_header):
    if raw_header is None:
        return None
    h = str(raw_header).strip().lower().replace('_', ' ').replace('-', ' ')
    # Normalize multiple whitespace to single space
    h = ' '.join(h.split())
    
    # Full Name mapping
    if h in ['full_name', 'fullname', 'full name', 'name', 'student name', 'candidate name']:
        return 'full_name'
    
    # Mobile Number mapping
    if h in ['mobile_number', 'mobilenumber', 'mobile number', 'mobile', 'phone', 'phone_number', 'phone number', 'contact number', 'contact_number']:
        return 'mobile_number'
    
    # Email mapping
    if h in ['email', 'email_address', 'email address']:
        return 'email'
    
    # City mapping
    if h in ['city', 'location']:
        return 'city'
    
    # Course interest mapping
    if h in ['course_interest', 'course interest', 'course']:
        return 'course_interest'
        
    # Source mapping
    if h in ['source']:
        return 'source'
        
    # Remarks mapping
    if h in ['remarks']:
        return 'remarks'
        
    return None


def format_cell_value(val):
    if val is None:
        return ''
    if isinstance(val, float):
        if val.is_integer():
            return str(int(val))
        return str(val)
    if isinstance(val, int):
        return str(val)
    return str(val).strip()


def log_lead_activity(lead, activity_type, description, user):
    created_by_user = user if (user and user.is_authenticated) else None
    LeadActivity.objects.create(
        lead=lead,
        activity_type=activity_type,
        description=description,
        created_by=created_by_user
    )


@login_required
@telecaller_required
def inquiry_import(request):
    if request.method == 'POST':
        file_data = request.FILES.get('file')
        if not file_data:
            messages.error(request, "Please select a file to upload.")
            return render(request, 'management/import.html')
            
        filename = file_data.name.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx')):
            messages.error(request, "Only CSV and Excel files are allowed.")
            return render(request, 'management/import.html')

        if filename.endswith('.csv'):
            try:
                import csv
                import io
                decoded_file = file_data.read().decode('utf-8-sig')
                io_string = io.StringIO(decoded_file)
                reader = csv.reader(io_string)
                header_row = next(reader, None)
                if not header_row:
                    messages.error(request, "The uploaded CSV file is empty.")
                    return render(request, 'management/import.html')
                
                mapped_headers = [map_header(h) for h in header_row]
                if 'full_name' not in mapped_headers or 'mobile_number' not in mapped_headers:
                    messages.error(request, "Missing required columns: full_name and mobile_number.")
                    return render(request, 'management/import.html')
                
                name_idx = mapped_headers.index('full_name')
                mobile_idx = mapped_headers.index('mobile_number')
                email_idx = mapped_headers.index('email') if 'email' in mapped_headers else -1
                city_idx = mapped_headers.index('city') if 'city' in mapped_headers else -1
                course_idx = mapped_headers.index('course_interest') if 'course_interest' in mapped_headers else -1
                source_idx = mapped_headers.index('source') if 'source' in mapped_headers else -1
                remarks_idx = mapped_headers.index('remarks') if 'remarks' in mapped_headers else -1

                lead_import = LeadImport.objects.create(
                    uploaded_by=request.user,
                    file=file_data,
                    total_records=0,
                    successful_records=0,
                    duplicate_records=0,
                    failed_records=0
                )

                total = 0
                success = 0
                duplicates = 0
                failed = 0
                row_idx = 1

                for row in reader:
                    if not row or not any(row):
                        continue
                    while len(row) < len(mapped_headers):
                        row.append(None)
                        
                    row_idx += 1
                    total += 1
                    full_name = format_cell_value(row[name_idx]).strip() if name_idx != -1 else ''
                    mobile_number = format_cell_value(row[mobile_idx]).strip() if mobile_idx != -1 else ''
                    
                    if not full_name:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Missing Full Name"
                        )
                        continue

                    if not mobile_number:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Missing Mobile Number"
                        )
                        continue
                        
                    if not mobile_number.isdigit() or len(mobile_number) < 10:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Invalid Mobile Number"
                        )
                        continue

                    if Inquiry.objects.filter(mobile_number=mobile_number).exists():
                        duplicates += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Duplicate Mobile Number"
                        )
                        continue

                    email = format_cell_value(row[email_idx]).strip() if email_idx != -1 else ''
                    city = format_cell_value(row[city_idx]).strip() if city_idx != -1 else ''
                    course_interest = format_cell_value(row[course_idx]).strip() if course_idx != -1 else ''
                    source = format_cell_value(row[source_idx]).strip() if source_idx != -1 else ''
                    remarks = format_cell_value(row[remarks_idx]).strip() if remarks_idx != -1 else ''

                    if email and ('@' not in email or '.' not in email):
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Invalid Email"
                        )
                        continue

                    matched_source = 'Website'
                    if source:
                        for c in Inquiry.SOURCE_CHOICES:
                            if c[0].lower() == source.lower():
                                matched_source = c[0]
                                break
                        else:
                            matched_source = 'Other'

                    Inquiry.objects.create(
                        full_name=full_name,
                        mobile_number=mobile_number,
                        email=email or None,
                        city=city,
                        course_interest=course_interest,
                        source=matched_source,
                        remarks=remarks,
                        status='New',
                        created_by=request.user
                    )
                    success += 1

                lead_import.total_records = total
                lead_import.successful_records = success
                lead_import.duplicate_records = duplicates
                lead_import.failed_records = failed
                lead_import.save()

                messages.success(request, (
                    f"Import summary:\n"
                    f"Total Records: {total}\n\n"
                    f"Imported Successfully: {success}\n\n"
                    f"Duplicate Records: {duplicates}\n\n"
                    f"Failed Records: {failed}"
                ))
                return redirect('import_history')
            except Exception as e:
                messages.error(request, f"Failed to process CSV file: {str(e)}")
                return render(request, 'management/import.html')

        elif filename.endswith('.xlsx'):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(file_data, read_only=True)
                sheet = wb.active
                rows_iter = sheet.iter_rows(values_only=True)
                header_row = next(rows_iter, None)
                if not header_row:
                    messages.error(request, "The uploaded Excel file is empty.")
                    return render(request, 'management/import.html')
                
                mapped_headers = [map_header(h) for h in header_row]
                if 'full_name' not in mapped_headers or 'mobile_number' not in mapped_headers:
                    messages.error(request, "Missing required columns: full_name and mobile_number.")
                    return render(request, 'management/import.html')
                
                name_idx = mapped_headers.index('full_name')
                mobile_idx = mapped_headers.index('mobile_number')
                email_idx = mapped_headers.index('email') if 'email' in mapped_headers else -1
                city_idx = mapped_headers.index('city') if 'city' in mapped_headers else -1
                course_idx = mapped_headers.index('course_interest') if 'course_interest' in mapped_headers else -1
                source_idx = mapped_headers.index('source') if 'source' in mapped_headers else -1
                remarks_idx = mapped_headers.index('remarks') if 'remarks' in mapped_headers else -1

                lead_import = LeadImport.objects.create(
                    uploaded_by=request.user,
                    file=file_data,
                    total_records=0,
                    successful_records=0,
                    duplicate_records=0,
                    failed_records=0
                )

                total = 0
                success = 0
                duplicates = 0
                failed = 0
                row_idx = 1

                for row in rows_iter:
                    if not row or not any(row):
                        continue
                    row_idx += 1
                    total += 1
                    
                    full_name = format_cell_value(row[name_idx]).strip() if name_idx != -1 else ''
                    mobile_number = format_cell_value(row[mobile_idx]).strip() if mobile_idx != -1 else ''
                    
                    if not full_name:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Missing Full Name"
                        )
                        continue

                    if not mobile_number:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Missing Mobile Number"
                        )
                        continue
                        
                    if not mobile_number.isdigit() or len(mobile_number) < 10:
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Invalid Mobile Number"
                        )
                        continue

                    if Inquiry.objects.filter(mobile_number=mobile_number).exists():
                        duplicates += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Duplicate Mobile Number"
                        )
                        continue

                    email = format_cell_value(row[email_idx]).strip() if email_idx != -1 else ''
                    city = format_cell_value(row[city_idx]).strip() if city_idx != -1 else ''
                    course_interest = format_cell_value(row[course_idx]).strip() if course_idx != -1 else ''
                    source = format_cell_value(row[source_idx]).strip() if source_idx != -1 else ''
                    remarks = format_cell_value(row[remarks_idx]).strip() if remarks_idx != -1 else ''

                    if email and ('@' not in email or '.' not in email):
                        failed += 1
                        ImportErrorLog.objects.create(
                            lead_import=lead_import,
                            row_number=row_idx,
                            error_message="Invalid Email"
                        )
                        continue

                    matched_source = 'Website'
                    if source:
                        for c in Inquiry.SOURCE_CHOICES:
                            if c[0].lower() == source.lower():
                                matched_source = c[0]
                                break
                        else:
                            matched_source = 'Other'

                    Inquiry.objects.create(
                        full_name=full_name,
                        mobile_number=mobile_number,
                        email=email or None,
                        city=city,
                        course_interest=course_interest,
                        source=matched_source,
                        remarks=remarks,
                        status='New',
                        created_by=request.user
                    )
                    success += 1

                lead_import.total_records = total
                lead_import.successful_records = success
                lead_import.duplicate_records = duplicates
                lead_import.failed_records = failed
                lead_import.save()

                messages.success(request, (
                    f"Import summary:\n"
                    f"Total Records: {total}\n\n"
                    f"Imported Successfully: {success}\n\n"
                    f"Duplicate Records: {duplicates}\n\n"
                    f"Failed Records: {failed}"
                ))
                return redirect('import_history')
            except Exception as e:
                messages.error(request, f"Failed to process Excel file: {str(e)}")
                return render(request, 'management/import.html')

    return render(request, 'management/import.html')


@login_required
@telecaller_required
def download_sample_csv(request):
    import csv
    from django.http import HttpResponse
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_inquiries.csv"'
    writer = csv.writer(response)
    writer.writerow(['full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'remarks'])
    writer.writerow(['Rahul Sharma', '9876543210', 'rahul.sharma@example.com', 'Thane', 'Java', 'Website', ''])
    writer.writerow(['Priya Patel', '9123456780', 'priya.patel@example.com', 'Mumbai', 'Python', 'Walk-In', ''])
    return response


@login_required
@telecaller_required
def download_sample_excel(request):
    import openpyxl
    from django.http import HttpResponse
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="sample_inquiries.xlsx"'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sample Inquiries"
    ws.append(['full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'remarks'])
    ws.append(['Rahul Sharma', '9876543210', 'rahul.sharma@example.com', 'Thane', 'Java', 'Website', ''])
    ws.append(['Priya Patel', '9123456780', 'priya.patel@example.com', 'Mumbai', 'Python', 'Walk-In', ''])
    wb.save(response)
    return response


@login_required
@telecaller_required
def import_history(request):
    if request.user.role == 'admin':
        imports = LeadImport.objects.all()
    else:
        imports = LeadImport.objects.filter(uploaded_by=request.user)

    paginator = Paginator(imports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/import_history.html', {
        'page_obj': page_obj,
    })


@login_required
@telecaller_required
def lead_notes_list(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead.")
        
    notes = lead.notes_timeline.all().order_by('created_at')
    return render(request, 'management/lead_notes.html', {
        'lead': lead,
        'notes': notes,
    })


@login_required
@telecaller_required
def lead_note_add(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead.")

    if request.method == 'POST':
        note_text = request.POST.get('note', '').strip()
        if note_text:
            LeadNote.objects.create(
                lead=lead,
                note=note_text,
                created_by=request.user
            )
            # Log activity
            log_lead_activity(lead, 'NOTE_ADDED', f"Note added: '{note_text[:50]}...'", request.user)
            messages.success(request, "Note added successfully.")
        else:
            messages.error(request, "Note content cannot be empty.")
        return redirect('lead_notes_list', pk=lead.pk)

    return render(request, 'management/lead_note_form.html', {'lead': lead})


@login_required
@telecaller_required
def activities_list(request):
    if request.user.role == 'admin':
        activities = LeadActivity.objects.all()
    else:
        activities = LeadActivity.objects.filter(lead__assigned_telecaller=request.user)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        activities = activities.filter(
            Q(lead__inquiry__full_name__icontains=q) | 
            Q(description__icontains=q) |
            Q(activity_type__icontains=q)
        )
    
    paginator = Paginator(activities, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/activity_timeline.html', {
        'page_obj': page_obj,
        'q': q,
    })


@login_required
@telecaller_required
def import_errors(request):
    import_id = request.GET.get('import_id')
    lead_import = None
    if import_id:
        lead_import = get_object_or_404(LeadImport, pk=import_id)
        if request.user.role != 'admin' and lead_import.uploaded_by != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this record.")
        errors = ImportErrorLog.objects.filter(lead_import=lead_import)
    else:
        if request.user.role == 'admin':
            errors = ImportErrorLog.objects.all()
        else:
            errors = ImportErrorLog.objects.filter(lead_import__uploaded_by=request.user)

    # Handle CSV export
    export = request.GET.get('export', '').strip()
    if export == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="import_errors_{import_id or "all"}.csv"'
        writer = csv.writer(response)
        writer.writerow(['Import ID', 'File Name', 'Row Number', 'Error Message', 'Timestamp'])
        for error in errors:
            writer.writerow([
                error.lead_import.id,
                error.lead_import.file.name,
                error.row_number,
                error.error_message,
                error.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        return response

    paginator = Paginator(errors, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/import_errors.html', {
        'page_obj': page_obj,
        'lead_import': lead_import,
        'import_id': import_id,
    })


@login_required
@telecaller_required
def lead_assign(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admin role required.")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    telecallers = User.objects.filter(role='telecaller')

    if request.method == 'POST':
        telecaller_id = request.POST.get('telecaller')
        lead_ids = request.POST.getlist('leads')
        
        # Or a single lead_id
        lead_id = request.POST.get('lead_id')
        if lead_id:
            lead_ids = [lead_id]

        if not telecaller_id:
            messages.error(request, "Please select a telecaller.")
        elif not lead_ids:
            messages.error(request, "Please select at least one lead.")
        else:
            telecaller = get_object_or_404(User, pk=telecaller_id)
            updated_count = 0
            for lid in lead_ids:
                lead = get_object_or_404(Lead, pk=lid)
                lead.assigned_telecaller = telecaller
                lead.assigned_by = request.user
                lead.assigned_at = timezone.now()
                lead.save()
                
                # Log assignment activity
                log_lead_activity(lead, 'ASSIGNED', f"Lead assigned to {telecaller.username} by admin {request.user.username}.", request.user)
                updated_count += 1
            
            messages.success(request, f"Successfully assigned {updated_count} lead(s) to {telecaller.username}.")
            return redirect('lead_assign')

    leads = Lead.objects.all()
    
    q = request.GET.get('q', '').strip()
    if q:
        leads = leads.filter(
            Q(inquiry__full_name__icontains=q) | Q(inquiry__mobile_number__icontains=q)
        )
    
    status = request.GET.get('status', '').strip()
    if status:
        leads = leads.filter(status=status)
        
    assigned_status = request.GET.get('assigned', '').strip()
    if assigned_status == 'yes':
        leads = leads.filter(assigned_telecaller__isnull=False)
    elif assigned_status == 'no':
        leads = leads.filter(assigned_telecaller__isnull=True)

    paginator = Paginator(leads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/lead_assignment.html', {
        'page_obj': page_obj,
        'telecallers': telecallers,
        'q': q,
        'status': status,
        'assigned': assigned_status,
        'status_choices': Lead.STATUS_CHOICES,
    })


@login_required
@telecaller_required
def lead_bulk_action(request):
    if request.method == 'POST':
        action = request.POST.get('action', '').strip()
        lead_ids = request.POST.getlist('leads')

        action_map = {
            'Mark Contacted': 'Contacted',
            'Mark Interested': 'Interested',
            'Mark Follow Up': 'Follow Up',
            'Mark Qualified': 'Qualified',
            'Mark Rejected': 'Rejected',
            'Mark Invalid Number': 'Invalid Number'
        }

        if not action or action not in action_map:
            messages.error(request, "Invalid action selected.")
            return redirect('lead_list')
        
        if not lead_ids:
            messages.error(request, "No leads selected.")
            return redirect('lead_list')

        status_value = action_map[action]
        success_count = 0

        for lid in lead_ids:
            lead = get_object_or_404(Lead, pk=lid)
            if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
                continue

            old_status = lead.status
            lead.status = status_value
            lead.save()

            log_lead_activity(lead, 'STATUS_CHANGED', f"Status updated via bulk action from {old_status} to {status_value}.", request.user)
            success_count += 1

        messages.success(request, f"Successfully executed '{action}' on {success_count} lead(s).")
        return redirect('lead_list')

    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_telecaller=request.user)

    paginator = Paginator(leads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/bulk_actions.html', {
        'page_obj': page_obj,
    })


@login_required
@telecaller_required
def reports_dashboard(request):
    sources = [choice[0] for choice in Inquiry.SOURCE_CHOICES]
    source_stats = []

    for src in sources:
        total_leads = Lead.objects.filter(inquiry__source=src).count()
        qualified_leads = Lead.objects.filter(inquiry__source=src, status='Qualified').count()
        rejected_leads = Lead.objects.filter(inquiry__source=src, status='Rejected').count()
        
        conversion_rate = 0.0
        if total_leads > 0:
            conversion_rate = round((qualified_leads / total_leads) * 100, 2)

        source_stats.append({
            'source': src,
            'total_leads': total_leads,
            'qualified_leads': qualified_leads,
            'rejected_leads': rejected_leads,
            'conversion_rate': conversion_rate,
        })

    chart_labels = sources
    source_distribution_data = [Lead.objects.filter(inquiry__source=src).count() for src in sources]
    conversion_by_source_data = []
    for src in sources:
        total = Lead.objects.filter(inquiry__source=src).count()
        qualified = Lead.objects.filter(inquiry__source=src, status='Qualified').count()
        rate = round((qualified / total) * 100, 2) if total > 0 else 0.0
        conversion_by_source_data.append(rate)

    return render(request, 'management/source_analytics.html', {
        'source_stats': source_stats,
        'chart_labels': chart_labels,
        'source_distribution_data': source_distribution_data,
        'conversion_by_source_data': conversion_by_source_data,
    })


@login_required
@telecaller_required
def telecaller_report(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if request.user.role == 'admin':
        telecallers = User.objects.filter(role='telecaller')
    else:
        telecallers = User.objects.filter(pk=request.user.pk)

    date_filter = request.GET.get('date_filter', 'this_month')
    start_date = None
    end_date = None
    today = datetime.date.today()

    if date_filter == 'today':
        start_date = today
        end_date = today
    elif date_filter == 'this_week':
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = today
    elif date_filter == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter == 'custom':
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        try:
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    report_data = []
    for tc in telecallers:
        inquiries_qs = Inquiry.objects.filter(created_by=tc)
        leads_qs = Lead.objects.filter(assigned_telecaller=tc)
        calls_qs = CallLog.objects.filter(created_by=tc)
        followups_qs = FollowUp.objects.filter(created_by=tc)

        if start_date:
            inquiries_qs = inquiries_qs.filter(created_at__date__gte=start_date)
            leads_qs = leads_qs.filter(created_at__date__gte=start_date)
            calls_qs = calls_qs.filter(call_date__date__gte=start_date)
            followups_qs = followups_qs.filter(followup_date__gte=start_date)
        if end_date:
            inquiries_qs = inquiries_qs.filter(created_at__date__lte=end_date)
            leads_qs = leads_qs.filter(created_at__date__lte=end_date)
            calls_qs = calls_qs.filter(call_date__date__lte=end_date)
            followups_qs = followups_qs.filter(followup_date__lte=end_date)

        total_inquiries = inquiries_qs.count()
        total_leads = leads_qs.count()
        calls_made = calls_qs.count()
        followups_completed = followups_qs.filter(status='Completed').count()
        qualified_leads = leads_qs.filter(status='Qualified').count()
        rejected_leads = leads_qs.filter(status='Rejected').count()
        pending_followups = followups_qs.filter(status='Pending').count()

        # Call Status Metrics
        cs_accepted = inquiries_qs.filter(call_status='ACCEPTED').count()
        cs_busy = inquiries_qs.filter(call_status='BUSY').count()
        cs_call_back = inquiries_qs.filter(call_status='CALL_BACK').count()
        cs_interested = inquiries_qs.filter(call_status='INTERESTED').count()
        cs_not_interested = inquiries_qs.filter(call_status='NOT_INTERESTED').count()

        conversion_pct = 0.0
        if total_leads > 0:
            conversion_pct = round((qualified_leads / total_leads) * 100, 2)

        report_data.append({
            'telecaller': tc.username,
            'total_inquiries': total_inquiries,
            'total_leads': total_leads,
            'calls_made': calls_made,
            'followups_completed': followups_completed,
            'qualified_leads': qualified_leads,
            'rejected_leads': rejected_leads,
            'pending_followups': pending_followups,
            'conversion_pct': conversion_pct,
            'cs_accepted': cs_accepted,
            'cs_busy': cs_busy,
            'cs_call_back': cs_call_back,
            'cs_interested': cs_interested,
            'cs_not_interested': cs_not_interested,
        })

    export_format = request.GET.get('export', '').strip()
    if export_format == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="telecaller_performance_report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Telecaller', 'Total Inquiries', 'Total Leads', 'Calls Made', 'Follow-Ups Completed', 'Qualified Leads', 'Rejected Leads', 'Pending Follow-Ups', 'Conversion %', 'Accepted', 'Busy', 'Call Back', 'Interested', 'Not Interested'])
        for row in report_data:
            writer.writerow([
                row['telecaller'], row['total_inquiries'], row['total_leads'], row['calls_made'],
                row['followups_completed'], row['qualified_leads'], row['rejected_leads'],
                row['pending_followups'], row['conversion_pct'],
                row['cs_accepted'], row['cs_busy'], row['cs_call_back'],
                row['cs_interested'], row['cs_not_interested']
            ])
        return response

    elif export_format == 'excel':
        import openpyxl
        from django.http import HttpResponse
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="telecaller_performance_report.xlsx"'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Performance Report"
        ws.append(['Telecaller', 'Total Inquiries', 'Total Leads', 'Calls Made', 'Follow-Ups Completed', 'Qualified Leads', 'Rejected Leads', 'Pending Follow-Ups', 'Conversion %', 'Accepted', 'Busy', 'Call Back', 'Interested', 'Not Interested'])
        for row in report_data:
            ws.append([
                row['telecaller'], row['total_inquiries'], row['total_leads'], row['calls_made'],
                row['followups_completed'], row['qualified_leads'], row['rejected_leads'],
                row['pending_followups'], row['conversion_pct'],
                row['cs_accepted'], row['cs_busy'], row['cs_call_back'],
                row['cs_interested'], row['cs_not_interested']
            ])
        wb.save(response)
        return response

    return render(request, 'management/telecaller_report.html', {
        'report_data': report_data,
        'date_filter': date_filter,
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
    })


# ==================================================
# COUNSELOR OPERATIONS (Phase 11.2)
# ==================================================

@login_required
@counselor_required
def counselor_dashboard(request):
    today = datetime.date.today()
    
    # Base Lead Queryset Scoping
    if request.user.role == 'admin':
        leads_qs = Lead.objects.all()
        calls_qs = CallLog.objects.all()
        followups_qs = FollowUp.objects.all()
        activities_qs = LeadActivity.objects.all()
    else:
        leads_qs = Lead.objects.filter(assigned_counselor=request.user)
        calls_qs = CallLog.objects.filter(lead__assigned_counselor=request.user)
        followups_qs = FollowUp.objects.filter(lead__assigned_counselor=request.user)
        activities_qs = LeadActivity.objects.filter(lead__assigned_counselor=request.user)

    # Counselor Status Counts
    total_assigned = leads_qs.count()
    new_leads = leads_qs.filter(counselor_status='NEW').count()
    contacted_leads = leads_qs.filter(counselor_status='CONTACTED').count()
    counseling_done = leads_qs.filter(counselor_status='COUNSELING_DONE').count()
    followup_req = leads_qs.filter(counselor_status='FOLLOW_UP_REQUIRED').count()
    interested_leads = leads_qs.filter(counselor_status='INTERESTED').count()
    converted_leads = leads_qs.filter(counselor_status='CONVERTED').count()
    not_interested = leads_qs.filter(counselor_status='NOT_INTERESTED').count()
    lost_leads = leads_qs.filter(counselor_status='LOST').count()
    
    # Followup statistics
    pending_followups = followups_qs.filter(status='Pending').count()
    overdue_followups = followups_qs.filter(status='Pending', followup_date__lt=today).count()

    # Visit statistics
    if request.user.role == 'admin':
        visits_qs = VisitSheet.objects.all()
    else:
        visits_qs = VisitSheet.objects.filter(counselor=request.user)

    today_visits = visits_qs.filter(visit_date=today).count()
    upcoming_visits = visits_qs.filter(visit_date__gt=today, status='Scheduled').count()
    completed_visits = visits_qs.filter(status__in=['Visited', 'Admission Done']).count()
    no_shows = visits_qs.filter(status='No Show').count()

    # Admission statistics
    if request.user.role == 'admin':
        admissions_qs = AdmissionSheet.objects.all()
    else:
        admissions_qs = AdmissionSheet.objects.filter(counselor=request.user)
    admission_metrics = {
        'total': admissions_qs.count(),
        'confirmed': admissions_qs.filter(admission_status='CONFIRMED').count(),
        'pending_payment': admissions_qs.filter(admission_status='PENDING_PAYMENT').count(),
        'cancelled': admissions_qs.filter(admission_status='CANCELLED').count(),
    }
    
    # Table Contexts
    recent_leads = leads_qs.order_by('-created_at')[:5]
    today_followups_list = followups_qs.filter(status='Pending', followup_date=today).order_by('followup_date')[:5]
    overdue_followups_list = followups_qs.filter(status='Pending', followup_date__lt=today).order_by('followup_date')[:5]
    recent_activities = activities_qs.order_by('-created_at')[:5]

    context = {
        'total_assigned': total_assigned,
        'new_leads': new_leads,
        'contacted_leads': contacted_leads,
        'counseling_done': counseling_done,
        'followup_req': followup_req,
        'interested_leads': interested_leads,
        'converted_leads': converted_leads,
        'not_interested': not_interested,
        'lost_leads': lost_leads,
        'pending_followups': pending_followups,
        'overdue_followups': overdue_followups,
        'recent_leads': recent_leads,
        'today_followups_list': today_followups_list,
        'overdue_followups_list': overdue_followups_list,
        'recent_activities': recent_activities,
        'today_visits': today_visits,
        'upcoming_visits': upcoming_visits,
        'completed_visits': completed_visits,
        'no_shows': no_shows,
        'admission_metrics': admission_metrics,
    }
    return render(request, 'management/counselor_dashboard.html', context)


@login_required
@counselor_required
def counselor_lead_list(request):
    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_counselor=request.user)

    # Search candidates
    q = request.GET.get('q', '').strip()
    if q:
        leads = leads.filter(
            Q(inquiry__full_name__icontains=q) | Q(inquiry__mobile_number__icontains=q)
        )

    # Filters
    status = request.GET.get('status', '').strip()
    if status:
        leads = leads.filter(counselor_status=status)

    priority = request.GET.get('priority', '').strip()
    if priority:
        leads = leads.filter(priority=priority)

    paginator = Paginator(leads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/counselor_lead_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'priority': priority,
        'status_choices': Lead.COUNSELOR_STATUS_CHOICES,
        'priority_choices': Lead.PRIORITY_CHOICES,
    })


@login_required
@counselor_required
def counselor_lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.user.role != 'admin' and lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead record.")

    sessions = lead.counseling_sessions.all().order_by('-session_date')
    followups = lead.followups.all().order_by('-followup_date')
    notes = lead.notes_timeline.all().order_by('-created_at')
    activities = lead.activities.all().order_by('-created_at')
    visits = lead.visit_sheets.all().order_by('-visit_date', '-visit_time')

    # Check admission sheet
    try:
        admission = lead.admission_sheet
    except AdmissionSheet.DoesNotExist:
        admission = None

    return render(request, 'management/counselor_lead_detail.html', {
        'lead': lead,
        'sessions': sessions,
        'followups': followups,
        'notes': notes,
        'activities': activities,
        'visits': visits,
        'admission': admission,
    })


@login_required
@counselor_required
def counselor_lead_status_update(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    if request.user.role != 'admin' and lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead record.")

    if request.method == 'POST':
        form = CounselorLeadStatusForm(request.POST, instance=lead)
        if form.is_valid():
            old_status = lead.counselor_status
            updated_lead = form.save(commit=False)
            updated_lead.counselor_status_updated_at = timezone.now()
            updated_lead.save()
            
            if old_status != updated_lead.counselor_status:
                log_lead_activity(
                    updated_lead, 
                    'STATUS_CHANGED', 
                    f"Counselor status updated from {old_status} to {updated_lead.counselor_status}.", 
                    request.user
                )
            
            messages.success(request, f"Counselor status updated successfully to {updated_lead.counselor_status}.")
            return redirect('counselor_lead_detail', pk=lead.pk)
    else:
        form = CounselorLeadStatusForm(instance=lead)
    return render(request, 'management/counselor_lead_status_update.html', {
        'form': form,
        'lead': lead,
    })


@login_required
@counselor_required
def counselor_session_list(request):
    if request.user.role == 'admin':
        sessions = CounselingSession.objects.all()
    else:
        sessions = CounselingSession.objects.filter(counselor=request.user)

    paginator = Paginator(sessions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/counselor_session_list.html', {
        'page_obj': page_obj,
    })


@login_required
@counselor_required
def counselor_session_add(request):
    lead_id = request.GET.get('lead_id')
    lead = None
    if lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
        if request.user.role != 'admin' and lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

    if request.method == 'POST':
        form = CounselingSessionForm(request.POST)
        selected_lead_id = request.POST.get('lead')
        selected_lead = get_object_or_404(Lead, pk=selected_lead_id)
        
        if request.user.role != 'admin' and selected_lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

        if form.is_valid():
            session = form.save(commit=False)
            session.lead = selected_lead
            session.counselor = request.user
            session.save()

            # Automatically transition lead status to COUNSELING_DONE
            if selected_lead.counselor_status != 'COUNSELING_DONE':
                old_status = selected_lead.counselor_status
                selected_lead.counselor_status = 'COUNSELING_DONE'
                selected_lead.counselor_status_updated_at = timezone.now()
                selected_lead.save()
                log_lead_activity(
                    selected_lead, 
                    'STATUS_CHANGED', 
                    f"Counselor status updated from {old_status} to COUNSELING_DONE upon recording session.", 
                    request.user
                )

            log_lead_activity(
                selected_lead, 
                'STATUS_CHANGED', 
                f"Counseling session recorded by {request.user.username}.", 
                request.user
            )
            messages.success(request, f"Counseling session recorded successfully for {selected_lead.inquiry.full_name}.")
            return redirect('counselor_lead_detail', pk=selected_lead.pk)
    else:
        form = CounselingSessionForm(initial={'lead': lead})

    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_counselor=request.user)

    return render(request, 'management/counselor_session_form.html', {
        'form': form,
        'leads': leads,
        'selected_lead': lead,
    })


@login_required
@counselor_required
def counselor_session_detail(request, pk):
    session = get_object_or_404(CounselingSession, pk=pk)
    if request.user.role != 'admin' and session.counselor != request.user:
        return HttpResponseForbidden("Access Denied: You did not record this counseling session.")

    return render(request, 'management/counselor_session_detail.html', {
        'session': session,
    })


@login_required
@counselor_required
def counselor_followup_list(request):
    if request.user.role == 'admin':
        followups = FollowUp.objects.all()
    else:
        followups = FollowUp.objects.filter(lead__assigned_counselor=request.user)

    status = request.GET.get('status', '').strip()
    if status:
        followups = followups.filter(status=status)

    paginator = Paginator(followups, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/counselor_followup_list.html', {
        'page_obj': page_obj,
        'status': status,
    })


@login_required
@counselor_required
def counselor_followup_add(request):
    lead_id = request.GET.get('lead_id')
    lead = None
    if lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
        if request.user.role != 'admin' and lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

    if request.method == 'POST':
        form = CounselorFollowUpForm(request.POST)
        selected_lead_id = request.POST.get('lead')
        selected_lead = get_object_or_404(Lead, pk=selected_lead_id)

        if request.user.role != 'admin' and selected_lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead.")

        if form.is_valid():
            followup = form.save(commit=False)
            followup.lead = selected_lead
            followup.created_by = request.user
            followup.save()

            # Sync dates and log activity
            selected_lead.next_followup_date = followup.followup_date
            # Transition lead status to FOLLOW_UP_REQUIRED
            if selected_lead.counselor_status != 'FOLLOW_UP_REQUIRED':
                old_status = selected_lead.counselor_status
                selected_lead.counselor_status = 'FOLLOW_UP_REQUIRED'
                selected_lead.counselor_status_updated_at = timezone.now()
                log_lead_activity(
                    selected_lead, 
                    'STATUS_CHANGED', 
                    f"Counselor status updated from {old_status} to FOLLOW_UP_REQUIRED upon scheduling follow-up.", 
                    request.user
                )
            selected_lead.save()

            log_lead_activity(selected_lead, 'FOLLOWUP_CREATED', f"Counselor follow-up scheduled for {followup.followup_date}.", request.user)
            messages.success(request, f"Follow-up scheduled successfully for {selected_lead.inquiry.full_name}.")
            return redirect('counselor_lead_detail', pk=selected_lead.pk)
    else:
        form = CounselorFollowUpForm(initial={'lead': lead})

    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_counselor=request.user)

    return render(request, 'management/counselor_followup_form.html', {
        'form': form,
        'leads': leads,
        'selected_lead': lead,
    })


@login_required
@counselor_required
def counselor_followup_edit(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role != 'admin' and followup.lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this followup record.")

    if request.method == 'POST':
        form = CounselorFollowUpForm(request.POST, instance=followup)
        if form.is_valid():
            fp = form.save()
            
            lead = fp.lead
            if fp.next_followup_date:
                lead.next_followup_date = fp.next_followup_date
            lead.save()

            messages.success(request, "Follow-up rescheduled successfully.")
            return redirect('counselor_lead_detail', pk=fp.lead.pk)
    else:
        form = CounselorFollowUpForm(instance=followup)

    return render(request, 'management/counselor_followup_form.html', {
        'form': form,
        'followup': followup,
        'selected_lead': followup.lead,
    })


@login_required
@counselor_required
def counselor_followup_complete(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role != 'admin' and followup.lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    followup.status = 'Completed'
    followup.save()
    log_lead_activity(followup.lead, 'FOLLOWUP_COMPLETED', f"Follow-up scheduled on {followup.followup_date} completed by counselor.", request.user)
    messages.success(request, "Follow-up marked as Completed.")
    return redirect('counselor_lead_detail', pk=followup.lead.pk)


@login_required
@counselor_required
def counselor_followup_miss(request, pk):
    followup = get_object_or_404(FollowUp, pk=pk)
    if request.user.role != 'admin' and followup.lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    followup.status = 'Missed'
    followup.save()
    log_lead_activity(followup.lead, 'FOLLOWUP_COMPLETED', f"Follow-up scheduled on {followup.followup_date} marked as Missed by counselor.", request.user)
    messages.warning(request, "Follow-up marked as Missed.")
    return redirect('counselor_lead_detail', pk=followup.lead.pk)


@login_required
@counselor_required
def counselor_note_add(request, lead_pk):
    lead = get_object_or_404(Lead, pk=lead_pk)
    if request.user.role != 'admin' and lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead record.")

    if request.method == 'POST':
        note_text = request.POST.get('note', '').strip()
        if note_text:
            LeadNote.objects.create(
                lead=lead,
                note=note_text,
                created_by=request.user
            )
            log_lead_activity(lead, 'NOTE_ADDED', f"Counselor note added: '{note_text[:50]}...'", request.user)
            messages.success(request, "Counselor note timeline updated successfully.")
        else:
            messages.error(request, "Note content cannot be empty.")
    return redirect('counselor_lead_detail', pk=lead.pk)


@login_required
@counselor_required
def counselor_reports_dashboard(request):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if request.user.role == 'admin':
        counselors = User.objects.filter(role='counselor')
    else:
        counselors = User.objects.filter(pk=request.user.pk)

    date_filter = request.GET.get('date_filter', 'this_month')
    start_date = None
    end_date = None
    today = datetime.date.today()

    if date_filter == 'today':
        start_date = today
        end_date = today
    elif date_filter == 'this_week':
        start_date = today - datetime.timedelta(days=today.weekday())
        end_date = today
    elif date_filter == 'this_month':
        start_date = today.replace(day=1)
        end_date = today
    elif date_filter == 'custom':
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        try:
            if start_date_str:
                start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    report_type = request.GET.get('report_type', 'performance').strip()
    report_data = []

    # Default values for visit metrics
    total_scheduled = 0
    total_completed = 0
    total_no_shows = 0
    total_admissions_visit = 0

    if report_type == 'visit':
        if request.user.role == 'admin':
            visits_qs = VisitSheet.objects.all()
        else:
            visits_qs = VisitSheet.objects.filter(counselor=request.user)

        if start_date:
            visits_qs = visits_qs.filter(visit_date__gte=start_date)
        if end_date:
            visits_qs = visits_qs.filter(visit_date__lte=end_date)

        total_scheduled = visits_qs.filter(status='Scheduled').count()
        total_completed = visits_qs.filter(status='Visited').count()
        total_no_shows = visits_qs.filter(status='No Show').count()
        total_admissions_visit = visits_qs.filter(status='Admission Done').count()

        for v in visits_qs:
            report_data.append({
                'candidate': v.lead.inquiry.full_name,
                'mobile_number': v.lead.inquiry.mobile_number,
                'course': v.lead.inquiry.course_interest,
                'visit_date': v.visit_date.strftime('%Y-%m-%d'),
                'visit_time': v.visit_time.strftime('%H:%M'),
                'status': v.status,
                'counselor': v.counselor.username,
                'remarks': v.remarks or '-',
            })

    elif report_type == 'performance':
        for cs in counselors:
            leads_qs = Lead.objects.filter(assigned_counselor=cs)
            sessions_qs = CounselingSession.objects.filter(counselor=cs)
            followups_qs = FollowUp.objects.filter(created_by=cs)

            if start_date:
                leads_qs = leads_qs.filter(created_at__date__gte=start_date)
                sessions_qs = sessions_qs.filter(created_at__date__gte=start_date)
                followups_qs = followups_qs.filter(created_at__date__gte=start_date)
            if end_date:
                leads_qs = leads_qs.filter(created_at__date__lte=end_date)
                sessions_qs = sessions_qs.filter(created_at__date__lte=end_date)
                followups_qs = followups_qs.filter(created_at__date__lte=end_date)

            total_leads = leads_qs.count()
            sessions_conducted = sessions_qs.count()
            followups_completed = followups_qs.filter(status='Completed').count()
            converted = leads_qs.filter(counselor_status='CONVERTED').count()
            lost = leads_qs.filter(counselor_status='LOST').count()

            conversion_pct = 0.0
            if total_leads > 0:
                conversion_pct = round((converted / total_leads) * 100, 2)

            report_data.append({
                'counselor': cs.username,
                'total_leads': total_leads,
                'sessions_conducted': sessions_conducted,
                'followups_completed': followups_completed,
                'converted': converted,
                'lost': lost,
                'conversion_pct': conversion_pct,
            })

    elif report_type == 'conversion':
        if request.user.role == 'admin':
            leads = Lead.objects.all()
        else:
            leads = Lead.objects.filter(assigned_counselor=request.user)

        if start_date:
            leads = leads.filter(created_at__date__gte=start_date)
        if end_date:
            leads = leads.filter(created_at__date__lte=end_date)

        for l in leads:
            report_data.append({
                'candidate': l.inquiry.full_name,
                'counselor': l.assigned_counselor.username if l.assigned_counselor else '-',
                'status': l.counselor_status,
                'priority': l.priority,
                'date': l.created_at.strftime('%Y-%m-%d')
            })

    elif report_type == 'followup':
        if request.user.role == 'admin':
            followups = FollowUp.objects.all()
        else:
            followups = FollowUp.objects.filter(lead__assigned_counselor=request.user)

        if start_date:
            followups = followups.filter(followup_date__gte=start_date)
        if end_date:
            followups = followups.filter(followup_date__lte=end_date)

        for fp in followups:
            report_data.append({
                'candidate': fp.lead.inquiry.full_name,
                'followup_date': fp.followup_date.strftime('%Y-%m-%d'),
                'status': fp.status,
                'outcome': fp.outcome or '-',
                'notes': fp.response or '-'
            })

    elif report_type == 'lost':
        if request.user.role == 'admin':
            leads = Lead.objects.filter(counselor_status='LOST')
        else:
            leads = Lead.objects.filter(assigned_counselor=request.user, counselor_status='LOST')

        if start_date:
            leads = leads.filter(counselor_status_updated_at__date__gte=start_date)
        if end_date:
            leads = leads.filter(counselor_status_updated_at__date__lte=end_date)

        for l in leads:
            report_data.append({
                'candidate': l.inquiry.full_name,
                'counselor': l.assigned_counselor.username if l.assigned_counselor else '-',
                'reason': l.notes or 'No details provided.',
                'date': l.counselor_status_updated_at.strftime('%Y-%m-%d') if l.counselor_status_updated_at else '-'
            })

    export_format = request.GET.get('export', '').strip()
    if export_format in ('csv', 'excel') and report_type == 'visit':
        return HttpResponseForbidden("Exporting is not supported for visit reports.")

    if export_format == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="counselor_{report_type}_report.csv"'
        writer = csv.writer(response)

        if report_type == 'performance':
            writer.writerow(['Counselor', 'Total Leads', 'Sessions Conducted', 'Follow-Ups Completed', 'Converted Leads', 'Lost Leads', 'Conversion %'])
            for row in report_data:
                writer.writerow([row['counselor'], row['total_leads'], row['sessions_conducted'], row['followups_completed'], row['converted'], row['lost'], row['conversion_pct']])
        elif report_type == 'conversion':
            writer.writerow(['Candidate Name', 'Counselor', 'Status', 'Priority', 'Assigned Date'])
            for row in report_data:
                writer.writerow([row['candidate'], row['counselor'], row['status'], row['priority'], row['date']])
        elif report_type == 'followup':
            writer.writerow(['Candidate Name', 'Follow-up Date', 'Status', 'Outcome', 'Notes'])
            for row in report_data:
                writer.writerow([row['candidate'], row['followup_date'], row['status'], row['outcome'], row['notes']])
        elif report_type == 'lost':
            writer.writerow(['Candidate Name', 'Counselor', 'Notes / Reason', 'Lost Date'])
            for row in report_data:
                writer.writerow([row['candidate'], row['counselor'], row['reason'], row['date']])

        return response

    elif export_format == 'excel':
        import openpyxl
        from django.http import HttpResponse
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="counselor_{report_type}_report.xlsx"'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = report_type.title()

        if report_type == 'performance':
            ws.append(['Counselor', 'Total Leads', 'Sessions Conducted', 'Follow-Ups Completed', 'Converted Leads', 'Lost Leads', 'Conversion %'])
            for row in report_data:
                ws.append([row['counselor'], row['total_leads'], row['sessions_conducted'], row['followups_completed'], row['converted'], row['lost'], row['conversion_pct']])
        elif report_type == 'conversion':
            ws.append(['Candidate Name', 'Counselor', 'Status', 'Priority', 'Assigned Date'])
            for row in report_data:
                ws.append([row['candidate'], row['counselor'], row['status'], row['priority'], row['date']])
        elif report_type == 'followup':
            ws.append(['Candidate Name', 'Follow-up Date', 'Status', 'Outcome', 'Notes'])
            for row in report_data:
                ws.append([row['candidate'], row['followup_date'], row['status'], row['outcome'], row['notes']])
        elif report_type == 'lost':
            ws.append(['Candidate Name', 'Counselor', 'Notes / Reason', 'Lost Date'])
            for row in report_data:
                ws.append([row['candidate'], row['counselor'], row['reason'], row['date']])

        wb.save(response)
        return response

    return render(request, 'management/counselor_reports.html', {
        'report_data': report_data,
        'report_type': report_type,
        'date_filter': date_filter,
        'start_date': request.GET.get('start_date', ''),
        'end_date': request.GET.get('end_date', ''),
        'total_scheduled': total_scheduled,
        'total_completed': total_completed,
        'total_no_shows': total_no_shows,
        'total_admissions_visit': total_admissions_visit,
    })


@login_required
def lead_assign_counselor(request):
    if request.user.role != 'admin':
        return HttpResponseForbidden("Access Denied: Admins only.")

    from django.contrib.auth import get_user_model
    User = get_user_model()
    counselors = User.objects.filter(role='counselor')

    if request.method == 'POST':
        counselor_id = request.POST.get('counselor')
        lead_ids = request.POST.getlist('leads')
        lead_id = request.POST.get('lead_id')
        if lead_id:
            lead_ids = [lead_id]

        if not counselor_id:
            messages.error(request, "Please select a counselor.")
        elif not lead_ids:
            messages.error(request, "Please select at least one lead.")
        else:
            counselor = get_object_or_404(User, pk=counselor_id)
            updated_count = 0
            for lid in lead_ids:
                lead = get_object_or_404(Lead, pk=lid)
                lead.assigned_counselor = counselor
                lead.save()
                
                log_lead_activity(lead, 'ASSIGNED', f"Lead assigned to Counselor {counselor.username} by admin {request.user.username}.", request.user)
                updated_count += 1
            
            messages.success(request, f"Successfully assigned {updated_count} lead(s) to Counselor {counselor.username}.")
            return redirect('lead_assign_counselor')

    leads = Lead.objects.all()
    q = request.GET.get('q', '').strip()
    if q:
        leads = leads.filter(
            Q(inquiry__full_name__icontains=q) | Q(inquiry__mobile_number__icontains=q)
        )
    
    status = request.GET.get('status', '').strip()
    if status:
        leads = leads.filter(counselor_status=status)
        
    assigned_status = request.GET.get('assigned', '').strip()
    if assigned_status == 'yes':
        leads = leads.filter(assigned_counselor__isnull=False)
    elif assigned_status == 'no':
        leads = leads.filter(assigned_counselor__isnull=True)

    paginator = Paginator(leads, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/counselor_assignment.html', {
        'page_obj': page_obj,
        'counselors': counselors,
        'q': q,
        'status': status,
        'assigned': assigned_status,
        'status_choices': Lead.COUNSELOR_STATUS_CHOICES,
    })


@login_required
@counselor_required
def counselor_visit_list(request):
    if request.user.role == 'admin':
        visits = VisitSheet.objects.all()
    elif request.user.role == 'counselor':
        visits = VisitSheet.objects.filter(counselor=request.user)
    else:
        return HttpResponseForbidden("Access Denied.")

    # Search candidates
    q = request.GET.get('q', '').strip()
    if q:
        visits = visits.filter(
            Q(lead__inquiry__full_name__icontains=q) |
            Q(lead__inquiry__mobile_number__icontains=q) |
            Q(lead__inquiry__course_interest__icontains=q)
        )

    # Filters
    status = request.GET.get('status', '').strip()
    if status:
        visits = visits.filter(status=status)

    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    if start_date:
        try:
            visits = visits.filter(visit_date__gte=datetime.datetime.strptime(start_date, "%Y-%m-%d").date())
        except ValueError:
            pass
    if end_date:
        try:
            visits = visits.filter(visit_date__lte=datetime.datetime.strptime(end_date, "%Y-%m-%d").date())
        except ValueError:
            pass

    paginator = Paginator(visits, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/counselor_visit_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'start_date': start_date,
        'end_date': end_date,
        'status_choices': VisitSheet.STATUS_CHOICES,
    })


@login_required
@counselor_required
def counselor_visit_add(request):
    lead_id = request.GET.get('lead_id')
    lead = None
    if lead_id:
        lead = get_object_or_404(Lead, pk=lead_id)
        if request.user.role != 'admin' and lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead record.")

    if request.method == 'POST':
        form = VisitSheetForm(request.POST, user=request.user)
        selected_lead_id = request.POST.get('lead')
        selected_lead = get_object_or_404(Lead, pk=selected_lead_id)

        if request.user.role != 'admin' and selected_lead.assigned_counselor != request.user:
            return HttpResponseForbidden("Access Denied: You do not own this lead record.")

        if form.is_valid():
            visit = form.save(commit=False)
            visit.lead = selected_lead
            visit.counselor = selected_lead.assigned_counselor or request.user
            visit.created_by = request.user
            visit.save()

            # Log activity
            log_lead_activity(
                selected_lead,
                'FOLLOWUP_CREATED',
                f"Visit scheduled for {visit.visit_date} at {visit.visit_time}.",
                request.user
            )

            messages.success(request, f"Visit scheduled successfully for {selected_lead.inquiry.full_name}.")
            return redirect('counselor_lead_detail', pk=selected_lead.pk)
    else:
        form = VisitSheetForm(initial={'lead': lead}, user=request.user)

    if request.user.role == 'admin':
        leads = Lead.objects.all()
    else:
        leads = Lead.objects.filter(assigned_counselor=request.user)

    return render(request, 'management/counselor_visit_form.html', {
        'form': form,
        'leads': leads,
        'selected_lead': lead,
        'title': 'Schedule Visit',
    })


@login_required
@counselor_required
def counselor_visit_edit(request, pk):
    visit = get_object_or_404(VisitSheet, pk=pk)
    if request.user.role != 'admin' and visit.counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this visit record.")

    if request.method == 'POST':
        form = VisitSheetForm(request.POST, instance=visit, user=request.user)
        if form.is_valid():
            old_status = visit.status
            updated_visit = form.save()

            if old_status != updated_visit.status:
                log_lead_activity(
                    updated_visit.lead,
                    'STATUS_CHANGED',
                    f"Visit status updated from {old_status} to {updated_visit.status}.",
                    request.user
                )

            messages.success(request, "Visit sheet updated successfully.")
            return redirect('counselor_lead_detail', pk=updated_visit.lead.pk)
    else:
        form = VisitSheetForm(instance=visit, user=request.user)

    return render(request, 'management/counselor_visit_form.html', {
        'form': form,
        'visit': visit,
        'selected_lead': visit.lead,
        'title': 'Edit Visit Sheet',
    })


# ==================================================
# PHASE 11.5 — ADMISSION SHEET MANAGEMENT
# ==================================================

@login_required
@counselor_required
def admission_list(request):
    """List all admissions with search, filters, and pagination."""
    if request.user.role == 'admin':
        admissions = AdmissionSheet.objects.all()
    else:
        admissions = AdmissionSheet.objects.filter(counselor=request.user)

    # Search
    q = request.GET.get('q', '').strip()
    if q:
        admissions = admissions.filter(
            Q(student_name__icontains=q) | Q(mobile_number__icontains=q) | Q(admission_number__icontains=q)
        )

    # Filters
    status = request.GET.get('status', '').strip()
    if status:
        admissions = admissions.filter(admission_status=status)

    counselor_id = request.GET.get('counselor', '').strip()
    if counselor_id and request.user.role == 'admin':
        admissions = admissions.filter(counselor_id=counselor_id)

    date_from = request.GET.get('date_from', '').strip()
    if date_from:
        admissions = admissions.filter(admission_date__gte=date_from)

    date_to = request.GET.get('date_to', '').strip()
    if date_to:
        admissions = admissions.filter(admission_date__lte=date_to)

    # Counselor choices for filter (admin only)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    counselor_choices = User.objects.filter(role='counselor').order_by('username')

    paginator = Paginator(admissions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/admission_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'counselor_id': counselor_id,
        'date_from': date_from,
        'date_to': date_to,
        'status_choices': AdmissionSheet.ADMISSION_STATUS_CHOICES,
        'counselor_choices': counselor_choices,
    })


@login_required
@counselor_required
def admission_create(request, lead_pk):
    """Create admission from a lead. Auto-populates student info."""
    lead = get_object_or_404(Lead, pk=lead_pk)
    if request.user.role != 'admin' and lead.assigned_counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this lead.")

    # Check duplicate
    if AdmissionSheet.objects.filter(lead=lead).exists():
        messages.error(request, "Admission Sheet already exists for this lead.")
        return redirect('counselor_lead_detail', pk=lead.pk)

    if request.method == 'POST':
        form = AdmissionSheetForm(request.POST)
        if form.is_valid():
            admission = form.save(commit=False)
            admission.lead = lead
            admission.created_by = request.user
            if not admission.counselor:
                admission.counselor = lead.assigned_counselor or request.user
            admission.save()

            # Update lead status to Admission Done
            lead.status = 'Admission Done'
            lead.counselor_status = 'CONVERTED'
            lead.counselor_status_updated_at = timezone.now()
            lead.save()

            log_lead_activity(
                lead,
                'STATUS_CHANGED',
                f"Admission Sheet created: {admission.admission_number}.",
                request.user
            )

            messages.success(request, f"Admission {admission.admission_number} created successfully.")
            return redirect('admission_detail', pk=admission.pk)
    else:
        # Auto-populate from lead
        inquiry = lead.inquiry
        initial = {
            'student_name': inquiry.full_name,
            'mobile_number': inquiry.mobile_number,
            'email_id': inquiry.email or '',
            'college_name': '',
            'department': '',
            'course_name': inquiry.course_interest or '',
            'admission_date': datetime.date.today(),
        }
        form = AdmissionSheetForm(initial=initial)

    return render(request, 'management/admission_form.html', {
        'form': form,
        'lead': lead,
        'title': 'Create Admission',
    })


@login_required
@counselor_required
def admission_edit(request, pk):
    """Edit an existing admission."""
    admission = get_object_or_404(AdmissionSheet, pk=pk)
    if request.user.role != 'admin' and admission.counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this admission record.")

    if request.method == 'POST':
        form = AdmissionSheetForm(request.POST, instance=admission)
        if form.is_valid():
            form.save()
            messages.success(request, f"Admission {admission.admission_number} updated successfully.")
            return redirect('admission_detail', pk=admission.pk)
    else:
        form = AdmissionSheetForm(instance=admission)

    return render(request, 'management/admission_form.html', {
        'form': form,
        'lead': admission.lead,
        'admission': admission,
        'title': 'Edit Admission',
    })


@login_required
@counselor_required
def admission_detail(request, pk):
    """View admission details."""
    admission = get_object_or_404(AdmissionSheet, pk=pk)
    if request.user.role != 'admin' and admission.counselor != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this admission record.")

    return render(request, 'management/admission_detail.html', {
        'admission': admission,
    })


@login_required
@counselor_required
def admission_report(request):
    """Simple admission report with tabular data."""
    if request.user.role == 'admin':
        admissions = AdmissionSheet.objects.all()
    else:
        admissions = AdmissionSheet.objects.filter(counselor=request.user)

    # Aggregate metrics
    from django.db.models import Sum, Count
    total_admissions = admissions.count()
    total_revenue = admissions.aggregate(total=Sum('fees_paid'))['total'] or 0
    total_outstanding = admissions.aggregate(total=Sum('remaining_fees'))['total'] or 0

    # By counselor
    by_counselor = admissions.values(
        'counselor__username'
    ).annotate(
        count=Count('id'),
        revenue=Sum('fees_paid'),
        outstanding=Sum('remaining_fees')
    ).order_by('-count')

    # By course
    by_course = admissions.values(
        'course_name'
    ).annotate(
        count=Count('id'),
        revenue=Sum('fees_paid'),
        outstanding=Sum('remaining_fees')
    ).order_by('-count')

    return render(request, 'management/admission_report.html', {
        'total_admissions': total_admissions,
        'total_revenue': total_revenue,
        'total_outstanding': total_outstanding,
        'by_counselor': by_counselor,
        'by_course': by_course,
    })
