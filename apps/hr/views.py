import csv
from collections import OrderedDict
from datetime import timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator

from apps.accounts.models import User
from .forms import (
    CandidateBasicForm,
    CandidateDocumentsForm,
    CandidateNoteForm,
    CandidateProfessionalForm,
    CandidateQuickForm,
    CandidateRecruitmentForm,
    CandidateStatusForm,
    FollowUpForm,
    HRSignupForm,
    InterviewFeedbackForm,
    InterviewForm,
    PlacementAssignmentForm,
    PlacementCompanyForm,
    PlacementDriveForm,
    PlacementInterviewForm,
    PlacementOfferForm,
)
from apps.students.models import StudentProfile
from .models import (
    Candidate,
    CandidateActivity,
    FollowUp,
    Interview,
    PlacementActivity,
    PlacementCompany,
    PlacementDrive,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
)


def hr_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'hr':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: HR only.")

    return wrapper


def signup_hr(request):
    if request.method == 'POST':
        form = HRSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'HR account created successfully. Please log in.')
            return redirect('login')
    else:
        form = HRSignupForm()

    return render(request, 'hr/signup.html', {'form': form})


def add_activity(candidate, activity_type, title, request=None, description=''):
    CandidateActivity.objects.create(
        candidate=candidate,
        activity_type=activity_type,
        title=title,
        description=description,
        created_by=request.user if request and request.user.is_authenticated else None,
    )


def add_placement_activity(activity_type, title, request=None, description='', company=None, drive=None):
    PlacementActivity.objects.create(
        activity_type=activity_type,
        title=title,
        description=description,
        company=company,
        drive=drive,
        created_by=request.user if request and request.user.is_authenticated else None,
    )


def hr_scope(queryset, request):
    if request.user.is_superuser:
        return queryset
    return queryset.filter(Q(assigned_hr=request.user) | Q(assigned_hr__isnull=True))


def trend_label(current, previous):
    if previous == 0:
        return '+100%' if current else '0%'
    diff = ((current - previous) / previous) * 100
    sign = '+' if diff >= 0 else ''
    return f'{sign}{diff:.0f}%'


def dashboard_metrics(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    candidates = hr_scope(Candidate.objects.all(), request)
    activities = CandidateActivity.objects.filter(candidate__in=candidates)
    followups = FollowUp.objects.filter(candidate__in=candidates)
    interviews = Interview.objects.filter(candidate__in=candidates)

    def metric(label, icon, color, value, current_filter, previous_filter):
        current = candidates.filter(current_filter).count() if current_filter else value
        previous = candidates.filter(previous_filter).count() if previous_filter else 0
        return {
            'label': label,
            'icon': icon,
            'color': color,
            'value': value,
            'trend': trend_label(current, previous),
            'spark': [max(8, min(100, value % 70 + 20)), max(8, min(100, current % 80 + 15)), max(8, min(100, (previous + value) % 90 + 10))],
        }

    calls_current = activities.filter(activity_type='call', created_at__date__gte=month_start).count()
    calls_previous = activities.filter(activity_type='call', created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end).count()
    interviews_current = interviews.filter(created_at__date__gte=month_start).count()
    interviews_previous = interviews.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end).count()
    pending_followups = followups.filter(completed=False, follow_up_date__gte=today).count()
    todays_activities = activities.filter(created_at__date=today).count()

    return [
        metric('Total Candidates', 'bi-people-fill', 'indigo', candidates.count(), Q(created_at__date__gte=month_start), Q(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end)),
        {'label': 'Calls Made', 'icon': 'bi-telephone-fill', 'color': 'emerald', 'value': calls_current, 'trend': trend_label(calls_current, calls_previous), 'spark': [22, 45, 70]},
        {'label': 'Interviews Scheduled', 'icon': 'bi-calendar-check-fill', 'color': 'blue', 'value': interviews.count(), 'trend': trend_label(interviews_current, interviews_previous), 'spark': [20, 62, 44]},
        metric('Selected', 'bi-patch-check-fill', 'orange', candidates.filter(status='selected').count(), Q(status='selected', updated_at__date__gte=month_start), Q(status='selected', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end)),
        metric('Rejected', 'bi-x-octagon-fill', 'red', candidates.filter(status='rejected').count(), Q(status='rejected', updated_at__date__gte=month_start), Q(status='rejected', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end)),
        metric('Joined', 'bi-person-check-fill', 'teal', candidates.filter(status='joined').count(), Q(status='joined', updated_at__date__gte=month_start), Q(status='joined', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end)),
        {'label': 'Pending Follow-ups', 'icon': 'bi-clock-fill', 'color': 'amber', 'value': pending_followups, 'trend': '+10%', 'spark': [44, 50, 72]},
        {'label': "Today's Activities", 'icon': 'bi-lightning-charge-fill', 'color': 'violet', 'value': todays_activities, 'trend': '+Today', 'spark': [18, 35, 58]},
    ]


def candidate_queryset(request):
    qs = hr_scope(Candidate.objects.select_related('assigned_hr'), request)
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    source = request.GET.get('source', '').strip()
    hr_id = request.GET.get('hr', '').strip()

    if query:
        qs = qs.filter(
            Q(full_name__icontains=query)
            | Q(mobile__icontains=query)
            | Q(email__icontains=query)
            | Q(applying_position__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    if source:
        qs = qs.filter(source=source)
    if hr_id:
        qs = qs.filter(assigned_hr_id=hr_id)
    return qs


@login_required
@hr_required
def dashboard(request):
    candidates = candidate_queryset(request)
    today = timezone.localdate()
    recent_candidates = candidates[:7]
    selected_candidate = candidates.first()
    status_counts = OrderedDict((key, candidates.filter(status=key).count()) for key, _ in Candidate.STATUS_CHOICES)
    hr_users = User.objects.filter(role='hr').order_by('username')
    hr_performance = [
        {
            'name': user.get_full_name() or user.username,
            'calls': CandidateActivity.objects.filter(candidate__assigned_hr=user, activity_type='call').count(),
            'selected': Candidate.objects.filter(assigned_hr=user, status__in=['selected', 'joined']).count(),
            'handled': Candidate.objects.filter(assigned_hr=user).count(),
        }
        for user in hr_users
    ]

    context = {
        'metrics': dashboard_metrics(request),
        'recent_candidates': recent_candidates,
        'selected_candidate': selected_candidate,
        'status_counts': status_counts,
        'status_total': max(sum(status_counts.values()), 1),
        'hr_performance': hr_performance,
        'todays_followups': FollowUp.objects.filter(candidate__in=candidates, completed=False, follow_up_date=today).count(),
        'pending_followups': FollowUp.objects.filter(candidate__in=candidates, completed=False).count(),
        'status_choices': Candidate.STATUS_CHOICES,
    }
    return render(request, 'hr/dashboard.html', context)


@login_required
@hr_required
def candidate_list(request):
    qs = candidate_queryset(request)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/candidate_list.html', {
        'page_obj': page_obj,
        'status_choices': Candidate.STATUS_CHOICES,
        'source_choices': Candidate.SOURCE_CHOICES,
        'hr_users': User.objects.filter(role='hr').order_by('username'),
        'query': request.GET.get('q', ''),
        'selected_status': request.GET.get('status', ''),
        'selected_source': request.GET.get('source', ''),
        'selected_hr': request.GET.get('hr', ''),
    })


@login_required
@hr_required
def candidate_create(request):
    forms = {
        'basic': CandidateBasicForm(request.POST or None, request.FILES or None, prefix='basic'),
        'professional': CandidateProfessionalForm(request.POST or None, request.FILES or None, prefix='professional'),
        'recruitment': CandidateRecruitmentForm(request.POST or None, request.FILES or None, prefix='recruitment'),
        'documents': CandidateDocumentsForm(request.POST or None, request.FILES or None, prefix='documents'),
    }
    if request.method == 'POST' and all(form.is_valid() for form in forms.values()):
        candidate = Candidate(created_by=request.user)
        for form in forms.values():
            for field, value in form.cleaned_data.items():
                setattr(candidate, field, value)
        if not candidate.assigned_hr:
            candidate.assigned_hr = request.user
        candidate.save()
        add_activity(candidate, 'created', 'Candidate Added', request, 'Candidate profile was created.')
        messages.success(request, 'Candidate added successfully.')
        return redirect('hr:candidate_detail', candidate_id=candidate.id)

    return render(request, 'hr/candidate_form.html', {'forms': forms, 'mode': 'add'})


@login_required
@hr_required
def candidate_edit(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    form = CandidateQuickForm(request.POST or None, request.FILES or None, instance=candidate)
    if request.method == 'POST' and form.is_valid():
        form.save()
        add_activity(candidate, 'document', 'Candidate Updated', request, 'Candidate profile information was updated.')
        messages.success(request, 'Candidate updated successfully.')
        return redirect('hr:candidate_detail', candidate_id=candidate.id)
    return render(request, 'hr/candidate_edit.html', {'form': form, 'candidate': candidate})


@login_required
@hr_required
def candidate_detail(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.select_related('assigned_hr'), request), id=candidate_id)
    note_form = CandidateNoteForm()
    status_form = CandidateStatusForm(instance=candidate)
    tab = request.GET.get('tab', 'overview')
    return render(request, 'hr/candidate_detail.html', {
        'candidate': candidate,
        'note_form': note_form,
        'status_form': status_form,
        'tab': tab,
    })


@login_required
@hr_required
def candidate_delete(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    if request.method == 'POST':
        candidate.delete()
        messages.success(request, 'Candidate deleted successfully.')
        return redirect('hr:candidate_list')
    return render(request, 'hr/confirm_delete.html', {'object': candidate, 'cancel_url': reverse('hr:candidate_detail', args=[candidate.id])})


@login_required
@hr_required
def mark_call(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    candidate.last_call_at = timezone.now()
    if candidate.status in ('new', 'no_response'):
        candidate.status = 'called'
    candidate.save(update_fields=['last_call_at', 'status', 'updated_at'])
    add_activity(candidate, 'call', 'Call Completed', request, 'Call activity was logged from HR dashboard.')
    messages.success(request, 'Call logged successfully.')
    return redirect(request.META.get('HTTP_REFERER') or 'hr:dashboard')


@login_required
@hr_required
def change_candidate_status(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    form = CandidateStatusForm(request.POST or None, instance=candidate)
    if request.method == 'POST' and form.is_valid():
        old_status = candidate.get_status_display()
        candidate = form.save()
        if candidate.status == 'joined' and not candidate.joined_at:
            candidate.joined_at = timezone.localdate()
            candidate.save(update_fields=['joined_at', 'updated_at'])
        add_activity(candidate, 'status', 'Status Changed', request, f'{old_status} to {candidate.get_status_display()}')
        messages.success(request, 'Candidate status updated.')
    return redirect('hr:candidate_detail', candidate_id=candidate.id)


@login_required
@hr_required
def add_note(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    form = CandidateNoteForm(request.POST)
    if form.is_valid():
        note = form.save(commit=False)
        note.candidate = candidate
        note.created_by = request.user
        note.save()
        add_activity(candidate, 'note', 'Note Added', request, note.note[:180])
        messages.success(request, 'Note added successfully.')
    return redirect(f"{reverse('hr:candidate_detail', args=[candidate.id])}?tab=notes")


@login_required
@hr_required
def followup_list(request):
    candidates = candidate_queryset(request)
    today = timezone.localdate()
    base = FollowUp.objects.select_related('candidate', 'handled_by').filter(candidate__in=candidates)
    bucket = request.GET.get('bucket', 'today')
    if bucket == 'upcoming':
        followups = base.filter(completed=False, follow_up_date__gt=today)
    elif bucket == 'overdue':
        followups = base.filter(completed=False, follow_up_date__lt=today)
    elif bucket == 'completed':
        followups = base.filter(completed=True)
    else:
        followups = base.filter(completed=False, follow_up_date=today)
    return render(request, 'hr/followup_list.html', {
        'followups': followups,
        'bucket': bucket,
        'counts': {
            'today': base.filter(completed=False, follow_up_date=today).count(),
            'upcoming': base.filter(completed=False, follow_up_date__gt=today).count(),
            'overdue': base.filter(completed=False, follow_up_date__lt=today).count(),
            'completed': base.filter(completed=True).count(),
        },
    })


@login_required
@hr_required
def followup_create(request, candidate_id=None):
    candidate = None
    if candidate_id:
        candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    form = FollowUpForm(request.POST or None, candidate=candidate)
    if request.method == 'POST' and form.is_valid():
        followup = form.save(commit=False)
        if candidate:
            followup.candidate = candidate
        followup.handled_by = request.user
        followup.save()
        if followup.candidate.status not in ('selected', 'rejected', 'joined'):
            followup.candidate.status = 'follow_up_pending'
            followup.candidate.save(update_fields=['status', 'updated_at'])
        add_activity(followup.candidate, 'followup', 'Follow-up Added', request, followup.remarks)
        messages.success(request, 'Follow-up saved successfully.')
        return redirect('hr:followup_list')
    return render(request, 'hr/followup_form.html', {'form': form, 'candidate': candidate})


@login_required
@hr_required
def followup_edit(request, followup_id):
    followup = get_object_or_404(FollowUp.objects.filter(candidate__in=hr_scope(Candidate.objects.all(), request)), id=followup_id)
    form = FollowUpForm(request.POST or None, instance=followup)
    if request.method == 'POST' and form.is_valid():
        followup = form.save()
        add_activity(followup.candidate, 'followup', 'Follow-up Updated', request, followup.remarks)
        messages.success(request, 'Follow-up updated successfully.')
        return redirect('hr:followup_list')
    return render(request, 'hr/followup_form.html', {'form': form, 'candidate': followup.candidate})


@login_required
@hr_required
def interview_list(request):
    candidates = candidate_queryset(request)
    interviews = Interview.objects.select_related('candidate', 'scheduled_by').filter(candidate__in=candidates)
    return render(request, 'hr/interview_list.html', {
        'interviews': interviews,
        'weekly_interviews': interviews.filter(date__gte=timezone.localdate(), date__lte=timezone.localdate() + timedelta(days=7)),
    })


@login_required
@hr_required
def interview_create(request, candidate_id=None):
    candidate = None
    if candidate_id:
        candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    form = InterviewForm(request.POST or None, candidate=candidate)
    if request.method == 'POST' and form.is_valid():
        interview = form.save(commit=False)
        if candidate:
            interview.candidate = candidate
        interview.scheduled_by = request.user
        interview.save()
        interview.candidate.status = 'interview_scheduled'
        interview.candidate.save(update_fields=['status', 'updated_at'])
        add_activity(interview.candidate, 'interview', 'Interview Scheduled', request, interview.get_interview_type_display())
        messages.success(request, 'Interview scheduled successfully.')
        return redirect('hr:interview_list')
    return render(request, 'hr/interview_form.html', {'form': form, 'candidate': candidate})


@login_required
@hr_required
def interview_feedback(request, interview_id):
    interview = get_object_or_404(Interview.objects.filter(candidate__in=hr_scope(Candidate.objects.all(), request)), id=interview_id)
    form = InterviewFeedbackForm(request.POST or None, instance=interview)
    if request.method == 'POST' and form.is_valid():
        interview = form.save()
        if interview.decision == 'select':
            interview.candidate.status = 'selected'
        elif interview.decision == 'reject':
            interview.candidate.status = 'rejected'
        elif interview.decision == 'hold':
            interview.candidate.status = 'on_hold'
        else:
            interview.candidate.status = 'interview_completed'
        interview.candidate.save(update_fields=['status', 'updated_at'])
        add_activity(interview.candidate, 'feedback', 'Interview Conducted', request, interview.remarks)
        messages.success(request, 'Interview feedback saved.')
        return redirect('hr:interview_list')
    return render(request, 'hr/interview_feedback.html', {'form': form, 'interview': interview})


@login_required
@hr_required
def reports(request):
    candidates = candidate_queryset(request)
    source_counts = OrderedDict((key, candidates.filter(source=key).count()) for key, _ in Candidate.SOURCE_CHOICES)
    status_counts = OrderedDict((key, candidates.filter(status=key).count()) for key, _ in Candidate.STATUS_CHOICES)
    total = max(candidates.count(), 1)
    return render(request, 'hr/reports.html', {
        'source_counts': source_counts,
        'status_counts': status_counts,
        'total': total,
        'interview_count': Interview.objects.filter(candidate__in=candidates).count(),
        'followup_count': FollowUp.objects.filter(candidate__in=candidates).count(),
        'selection_ratio': round((candidates.filter(status__in=['selected', 'joined']).count() / total) * 100, 1),
    })


@login_required
@hr_required
def performance(request):
    users = User.objects.filter(role='hr').order_by('username')
    rows = []
    for user in users:
        handled = Candidate.objects.filter(assigned_hr=user).count()
        selected = Candidate.objects.filter(assigned_hr=user, status__in=['selected', 'joined']).count()
        rejected = Candidate.objects.filter(assigned_hr=user, status='rejected').count()
        calls = CandidateActivity.objects.filter(candidate__assigned_hr=user, activity_type='call').count()
        interviews = Interview.objects.filter(candidate__assigned_hr=user).count()
        rows.append({
            'user': user,
            'handled': handled,
            'selected': selected,
            'rejected': rejected,
            'calls': calls,
            'interviews': interviews,
            'conversion': round((selected / handled) * 100, 1) if handled else 0,
        })
    rows.sort(key=lambda item: (item['conversion'], item['selected'], item['handled']), reverse=True)
    return render(request, 'hr/performance.html', {'rows': rows})


@login_required
@hr_required
def export_candidates(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="hr-candidates.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Mobile', 'Email', 'Applying For', 'Department', 'Assigned HR', 'Status', 'Source', 'Date Added'])
    for candidate in candidate_queryset(request):
        writer.writerow([
            candidate.full_name,
            candidate.mobile,
            candidate.email,
            candidate.applying_position,
            candidate.department,
            candidate.assigned_hr.username if candidate.assigned_hr else '',
            candidate.get_status_display(),
            candidate.get_source_display(),
            candidate.date_added,
        ])
    return response


def placement_metrics():
    total_sent = PlacementStudentAssignment.objects.count()
    selected = PlacementStudentAssignment.objects.filter(final_status__in=['selected', 'joined']).count()
    rejected = PlacementStudentAssignment.objects.filter(final_status='rejected').count()
    placed = PlacementStudentAssignment.objects.filter(final_status='joined').count()
    rate = round((placed / total_sent) * 100, 2) if total_sent else 0
    return [
        {'label': 'Total Companies', 'icon': 'bi-buildings-fill', 'color': 'violet', 'value': PlacementCompany.objects.count(), 'trend': '+8 this month', 'spark': [22, 55, 70]},
        {'label': 'Total Drives', 'icon': 'bi-megaphone-fill', 'color': 'emerald', 'value': PlacementDrive.objects.count(), 'trend': '+3 this month', 'spark': [30, 45, 68]},
        {'label': 'Students Eligible', 'icon': 'bi-mortarboard-fill', 'color': 'blue', 'value': StudentProfile.objects.count(), 'trend': '+24 this month', 'spark': [18, 55, 86]},
        {'label': 'Students Sent', 'icon': 'bi-send-fill', 'color': 'orange', 'value': total_sent, 'trend': '+15 this month', 'spark': [28, 62, 73]},
        {'label': 'Students Selected', 'icon': 'bi-person-check-fill', 'color': 'teal', 'value': selected, 'trend': '+10 this month', 'spark': [18, 42, 64]},
        {'label': 'Students Rejected', 'icon': 'bi-person-x-fill', 'color': 'red', 'value': rejected, 'trend': '+4 this month', 'spark': [12, 35, 40]},
        {'label': 'Students Placed', 'icon': 'bi-award-fill', 'color': 'indigo', 'value': placed, 'trend': '+5 this month', 'spark': [12, 44, 66]},
        {'label': 'Placement Rate', 'icon': 'bi-graph-up-arrow', 'color': 'amber', 'value': f'{rate}%', 'trend': '+3.45% this month', 'spark': [20, 58, 78]},
    ]


@login_required
@hr_required
def placement_dashboard(request):
    drives = PlacementDrive.objects.select_related('company')[:6]
    status_counts = OrderedDict((key, PlacementDrive.objects.filter(status=key).count()) for key, _ in PlacementDrive.STATUS_CHOICES)
    total_drives = max(sum(status_counts.values()), 1)
    top_companies = sorted(PlacementCompany.objects.all(), key=lambda company: company.joined_count, reverse=True)[:5]
    context = {
        'metrics': placement_metrics(),
        'recent_drives': drives,
        'top_companies': top_companies,
        'status_counts': status_counts,
        'total_drives': total_drives,
        'activities': PlacementActivity.objects.select_related('company', 'drive', 'created_by')[:6],
        'upcoming_interviews': PlacementInterview.objects.select_related('company', 'drive', 'assignment')[:5],
        'pipeline': {
            'scheduled': PlacementDrive.objects.exclude(status='cancelled').count(),
            'shortlisted': PlacementStudentAssignment.objects.count(),
            'appeared': PlacementStudentAssignment.objects.filter(interview_status__in=['appeared', 'selected', 'rejected']).count(),
            'offers': PlacementOffer.objects.exclude(offer_status='pending').count(),
            'placed': PlacementStudentAssignment.objects.filter(final_status='joined').count(),
        },
    }
    return render(request, 'hr/placement_dashboard.html', context)


@login_required
@hr_required
def placement_company_list(request):
    companies = PlacementCompany.objects.all()
    query = request.GET.get('q', '').strip()
    if query:
        companies = companies.filter(
            Q(name__icontains=query)
            | Q(industry__icontains=query)
            | Q(contact_person__icontains=query)
            | Q(city__icontains=query)
        )
    page_obj = Paginator(companies, 12).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_company_list.html', {'page_obj': page_obj, 'query': query})


@login_required
@hr_required
def placement_company_create(request):
    form = PlacementCompanyForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        company = form.save(commit=False)
        company.created_by = request.user
        company.save()
        add_placement_activity('company', f'{company} added', request, 'Company profile saved.', company=company)
        messages.success(request, 'Company saved successfully.')
        return redirect('hr:placement_company_detail', company_id=company.id)
    return render(request, 'hr/placement_company_form.html', {'form': form, 'title': 'Add Company'})


@login_required
@hr_required
def placement_company_edit(request, company_id):
    company = get_object_or_404(PlacementCompany, id=company_id)
    form = PlacementCompanyForm(request.POST or None, request.FILES or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        company = form.save()
        add_placement_activity('company', f'{company} updated', request, 'Company profile updated.', company=company)
        messages.success(request, 'Company updated successfully.')
        return redirect('hr:placement_company_detail', company_id=company.id)
    return render(request, 'hr/placement_company_form.html', {'form': form, 'title': 'Edit Company', 'company': company})


@login_required
@hr_required
def placement_company_detail(request, company_id):
    company = get_object_or_404(PlacementCompany, id=company_id)
    assignments = company.placement_assignments.select_related('student', 'drive')[:20]
    return render(request, 'hr/placement_company_detail.html', {'company': company, 'assignments': assignments})


@login_required
@hr_required
def placement_company_delete(request, company_id):
    company = get_object_or_404(PlacementCompany, id=company_id)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Company deleted successfully.')
        return redirect('hr:placement_company_list')
    return render(request, 'hr/confirm_delete.html', {'object': company, 'cancel_url': reverse('hr:placement_company_detail', args=[company.id])})


@login_required
@hr_required
def placement_drive_list(request):
    drives = PlacementDrive.objects.select_related('company')
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    if status:
        drives = drives.filter(status=status)
    if query:
        drives = drives.filter(Q(company__name__icontains=query) | Q(job_role__icontains=query) | Q(venue__icontains=query))
    page_obj = Paginator(drives, 12).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_drive_list.html', {
        'page_obj': page_obj,
        'status_choices': PlacementDrive.STATUS_CHOICES,
        'status': status,
        'query': query,
    })


@login_required
@hr_required
def placement_drive_create(request, company_id=None):
    company = get_object_or_404(PlacementCompany, id=company_id) if company_id else None
    form = PlacementDriveForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        drive = form.save(commit=False)
        if company:
            drive.company = company
        drive.created_by = request.user
        drive.save()
        add_placement_activity('drive', f'{drive} created', request, 'Placement drive scheduled.', company=drive.company, drive=drive)
        messages.success(request, 'Placement drive saved successfully.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_drive_form.html', {'form': form, 'company': company})


@login_required
@hr_required
def placement_drive_edit(request, drive_id):
    drive = get_object_or_404(PlacementDrive, id=drive_id)
    form = PlacementDriveForm(request.POST or None, instance=drive)
    if request.method == 'POST' and form.is_valid():
        drive = form.save()
        add_placement_activity('drive', f'{drive} updated', request, 'Placement drive updated.', company=drive.company, drive=drive)
        messages.success(request, 'Placement drive updated successfully.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_drive_form.html', {'form': form, 'drive': drive})


@login_required
@hr_required
def placement_drive_detail(request, drive_id):
    drive = get_object_or_404(PlacementDrive.objects.select_related('company'), id=drive_id)
    assignments = drive.assignments.select_related('student', 'company')[:30]
    return render(request, 'hr/placement_drive_detail.html', {'drive': drive, 'assignments': assignments})


@login_required
@hr_required
def placement_assign_students(request, drive_id):
    drive = get_object_or_404(PlacementDrive.objects.select_related('company'), id=drive_id)
    assigned_ids = list(drive.assignments.filter(student__isnull=False).values_list('student_id', flat=True))
    students = StudentProfile.objects.select_related('batch', 'batch__course').exclude(id__in=assigned_ids).order_by('full_name')
    query = request.GET.get('q', '').strip()
    if query:
        students = students.filter(Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(email__icontains=query))
    if request.method == 'POST':
        selected_ids = request.POST.getlist('students')
        created = 0
        for student in StudentProfile.objects.filter(id__in=selected_ids):
            PlacementStudentAssignment.objects.get_or_create(
                drive=drive,
                student=student,
                defaults={
                    'company': drive.company,
                    'student_name': student.full_name,
                    'course_name': student.batch.course.name if student.batch and student.batch.course else '',
                    'assigned_by': request.user,
                },
            )
            created += 1
        if created:
            add_placement_activity('assignment', f'{created} students assigned to {drive.company or drive}', request, drive=drive, company=drive.company)
        messages.success(request, f'{created} students assigned successfully.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_assign_students.html', {'drive': drive, 'students': students[:100], 'query': query})


@login_required
@hr_required
def placement_student_list(request):
    assignments = PlacementStudentAssignment.objects.select_related('student', 'company', 'drive')
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    if status:
        assignments = assignments.filter(final_status=status)
    if query:
        assignments = assignments.filter(Q(student_name__icontains=query) | Q(student__full_name__icontains=query) | Q(company__name__icontains=query))
    page_obj = Paginator(assignments, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_student_list.html', {
        'page_obj': page_obj,
        'status_choices': PlacementStudentAssignment.FINAL_STATUS_CHOICES,
        'status': status,
        'query': query,
    })


@login_required
@hr_required
def placement_assignment_create(request, drive_id=None, company_id=None):
    drive = get_object_or_404(PlacementDrive, id=drive_id) if drive_id else None
    company = get_object_or_404(PlacementCompany, id=company_id) if company_id else None
    form = PlacementAssignmentForm(request.POST or None, drive=drive, company=company)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        if drive:
            assignment.drive = drive
            assignment.company = drive.company
        elif company:
            assignment.company = company
        if assignment.student:
            assignment.student_name = assignment.student_name or assignment.student.full_name
            if not assignment.course_name and assignment.student.batch and assignment.student.batch.course:
                assignment.course_name = assignment.student.batch.course.name
        assignment.assigned_by = request.user
        assignment.save()
        add_placement_activity('assignment', f'{assignment.display_name} assigned to {assignment.company or "company"}', request, company=assignment.company, drive=assignment.drive)
        messages.success(request, 'Student assignment saved successfully.')
        return redirect('hr:placement_student_list')
    return render(request, 'hr/placement_assignment_form.html', {'form': form, 'drive': drive, 'company': company})


@login_required
@hr_required
def placement_assignment_edit(request, assignment_id):
    assignment = get_object_or_404(PlacementStudentAssignment, id=assignment_id)
    form = PlacementAssignmentForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save()
        messages.success(request, 'Student placement updated successfully.')
        return redirect('hr:placement_student_list')
    return render(request, 'hr/placement_assignment_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def placement_interview_list(request):
    interviews = PlacementInterview.objects.select_related('company', 'drive', 'assignment')
    page_obj = Paginator(interviews, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_interview_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def placement_interview_create(request, drive_id=None, assignment_id=None):
    drive = get_object_or_404(PlacementDrive, id=drive_id) if drive_id else None
    assignment = get_object_or_404(PlacementStudentAssignment, id=assignment_id) if assignment_id else None
    form = PlacementInterviewForm(request.POST or None, drive=drive, assignment=assignment)
    if request.method == 'POST' and form.is_valid():
        interview = form.save(commit=False)
        if assignment:
            interview.assignment = assignment
            interview.company = assignment.company
            interview.drive = assignment.drive
        elif drive:
            interview.drive = drive
            interview.company = drive.company
        interview.created_by = request.user
        interview.save()
        if interview.assignment:
            interview.assignment.interview_status = interview.status
            interview.assignment.save(update_fields=['interview_status', 'updated_at'])
        add_placement_activity('interview', f'Interview scheduled for {interview.assignment or interview.company or "student"}', request, company=interview.company, drive=interview.drive)
        messages.success(request, 'Placement interview saved successfully.')
        return redirect('hr:placement_interview_list')
    return render(request, 'hr/placement_interview_form.html', {'form': form, 'drive': drive, 'assignment': assignment})


@login_required
@hr_required
def placement_interview_edit(request, interview_id):
    interview = get_object_or_404(PlacementInterview, id=interview_id)
    form = PlacementInterviewForm(request.POST or None, instance=interview)
    if request.method == 'POST' and form.is_valid():
        interview = form.save()
        if interview.assignment:
            interview.assignment.interview_status = interview.status
            if interview.status == 'selected':
                interview.assignment.final_status = 'selected'
            elif interview.status == 'rejected':
                interview.assignment.final_status = 'rejected'
            interview.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        messages.success(request, 'Placement interview updated successfully.')
        return redirect('hr:placement_interview_list')
    return render(request, 'hr/placement_interview_form.html', {'form': form, 'interview': interview})


@login_required
@hr_required
def placement_offer_list(request):
    offers = PlacementOffer.objects.select_related('assignment', 'assignment__student', 'company')
    page_obj = Paginator(offers, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_offer_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def placement_offer_create(request, assignment_id=None):
    assignment = get_object_or_404(PlacementStudentAssignment, id=assignment_id) if assignment_id else None
    instance = PlacementOffer.objects.filter(assignment=assignment).first() if assignment else None
    form = PlacementOfferForm(request.POST or None, assignment=assignment, instance=instance)
    if request.method == 'POST' and form.is_valid():
        offer = form.save(commit=False)
        if assignment:
            offer.assignment = assignment
            offer.company = assignment.company
        offer.created_by = offer.created_by or request.user
        offer.save()
        if offer.assignment:
            if offer.joining_status == 'joined':
                offer.assignment.final_status = 'joined'
            elif offer.offer_status in ('offered', 'accepted'):
                offer.assignment.final_status = 'selected'
            elif offer.offer_status == 'rejected':
                offer.assignment.final_status = 'rejected'
            offer.assignment.save(update_fields=['final_status', 'updated_at'])
        add_placement_activity('offer', f'Offer updated for {offer.assignment or offer.company}', request, company=offer.company)
        messages.success(request, 'Offer and placement saved successfully.')
        return redirect('hr:placement_offer_list')
    return render(request, 'hr/placement_offer_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def placement_offer_edit(request, offer_id):
    offer = get_object_or_404(PlacementOffer, id=offer_id)
    form = PlacementOfferForm(request.POST or None, instance=offer)
    if request.method == 'POST' and form.is_valid():
        offer = form.save()
        messages.success(request, 'Offer updated successfully.')
        return redirect('hr:placement_offer_list')
    return render(request, 'hr/placement_offer_form.html', {'form': form, 'offer': offer})


@login_required
@hr_required
def placement_reports(request):
    companies = PlacementCompany.objects.all()
    assignments = PlacementStudentAssignment.objects.select_related('company', 'drive', 'student')
    company_id = request.GET.get('company', '').strip()
    status = request.GET.get('status', '').strip()
    if company_id:
        assignments = assignments.filter(company_id=company_id)
    if status:
        assignments = assignments.filter(final_status=status)
    return render(request, 'hr/placement_reports.html', {
        'companies': companies,
        'assignments': assignments[:100],
        'company_id': company_id,
        'status': status,
        'status_choices': PlacementStudentAssignment.FINAL_STATUS_CHOICES,
        'summary': {
            'companies': companies.count(),
            'drives': PlacementDrive.objects.count(),
            'sent': PlacementStudentAssignment.objects.count(),
            'selected': PlacementStudentAssignment.objects.filter(final_status__in=['selected', 'joined']).count(),
            'joined': PlacementStudentAssignment.objects.filter(final_status='joined').count(),
        },
    })


@login_required
@hr_required
def export_placement_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="placement-report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Student', 'Course', 'Company', 'Drive', 'Interview Status', 'Final Status'])
    for item in PlacementStudentAssignment.objects.select_related('student', 'company', 'drive'):
        writer.writerow([
            item.display_name,
            item.display_course,
            item.company.name if item.company else '',
            item.drive.job_role if item.drive else '',
            item.get_interview_status_display(),
            item.get_final_status_display(),
        ])
    return response


@login_required
@hr_required
def simple_section(request, section):
    titles = {
        'placement': 'Placement',
        'external-hiring': 'External Hiring',
        'projects': 'Projects',
        'calendar': 'Calendar',
        'settings': 'Settings',
    }
    return render(request, 'hr/section.html', {'title': titles.get(section, 'HR Section')})
