from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
import datetime

from .models import Inquiry, Lead, CallLog, FollowUp
from .forms import InquiryForm, LeadForm, CallLogForm, FollowUpForm
from .decorators import telecaller_required

@login_required
@telecaller_required
def management_dashboard(request):
    today = datetime.date.today()
    
    # Base Querysets with Data Isolation
    if request.user.role == 'admin':
        inquiries_qs = Inquiry.objects.all()
        leads_qs = Lead.objects.all()
        calls_qs = CallLog.objects.all()
        followups_qs = FollowUp.objects.all()
    else:
        inquiries_qs = Inquiry.objects.filter(created_by=request.user)
        leads_qs = Lead.objects.filter(assigned_telecaller=request.user)
        calls_qs = CallLog.objects.filter(created_by=request.user)
        followups_qs = FollowUp.objects.filter(created_by=request.user)

    # Statistics Calculation
    total_inquiries = inquiries_qs.count()
    new_inquiries = inquiries_qs.filter(status='New').count()
    total_leads = leads_qs.count()
    today_calls = calls_qs.filter(call_date__date=today).count()
    pending_followups = followups_qs.filter(status='Pending').count()
    qualified_leads = leads_qs.filter(status='Qualified').count()

    # Tables
    recent_inquiries = inquiries_qs.order_by('-created_at')[:5]
    today_followups = followups_qs.filter(status='Pending', followup_date__lte=today).order_by('followup_date')[:5]
    recent_call_logs = calls_qs.order_by('-call_date')[:5]

    context = {
        'total_inquiries': total_inquiries,
        'new_inquiries': new_inquiries,
        'total_leads': total_leads,
        'today_calls': today_calls,
        'pending_followups': pending_followups,
        'qualified_leads': qualified_leads,
        'recent_inquiries': recent_inquiries,
        'today_followups': today_followups,
        'recent_call_logs': recent_call_logs,
    }
    return render(request, 'management/dashboard.html', context)


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

    paginator = Paginator(inquiries, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'management/inquiry_list.html', {
        'page_obj': page_obj,
        'q': q,
        'status': status,
        'source': source,
        'status_choices': Inquiry.STATUS_CHOICES,
        'source_choices': Inquiry.SOURCE_CHOICES,
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
            priority='Medium'
        )
        # Auto-update Inquiry status to Qualified
        inquiry.status = 'Qualified'
        inquiry.save()

        messages.success(request, f"Inquiry for {inquiry.full_name} converted to Lead successfully.")
        return redirect('lead_detail', pk=lead.pk)

    return render(request, 'management/inquiry_convert.html', {'inquiry': inquiry})


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

    return render(request, 'management/lead_detail.html', {
        'lead': lead,
        'call_logs': call_logs,
        'followups': followups,
    })


@login_required
@telecaller_required
def lead_edit(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    # Security Data Isolation
    if request.user.role != 'admin' and lead.assigned_telecaller != request.user:
        return HttpResponseForbidden("Access Denied: You do not own this record.")

    if request.method == 'POST':
        form = LeadForm(request.POST, instance=lead)
        if form.is_valid():
            form.save()
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
    messages.success(request, "Follow-up marked as Completed.")
    return redirect('lead_detail', pk=followup.lead.pk)
