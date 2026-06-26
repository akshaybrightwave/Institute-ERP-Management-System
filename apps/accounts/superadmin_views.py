import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .auth_logging import log_auth_activity
from .forms import SuperAdminPasswordResetForm, SuperAdminUserCreationForm, SuperAdminUserEditForm
from .models import AuthActivityLog, SuperAdminExport, SuperAdminNotification, User
from apps.hr.models import (
    Candidate,
    CandidateActivity,
    ExternalAttendanceLog,
    ExternalEmployee,
    FollowUp as HRFollowUp,
    Interview as HRInterview,
    PlacementCompany,
    PlacementDrive,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
    ProjectAllocation,
    ProjectCompany,
    ProjectDrive,
    ProjectEmployeeAssignment,
    ProjectInterview,
)
from apps.management.models import (
    AdmissionSheet,
    CallLog,
    CounselingSession,
    FollowUp as ManagementFollowUp,
    Inquiry,
    Lead,
    LeadActivity,
    VisitSheet,
)


def super_admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'SUPER_ADMIN':
            return view_func(request, *args, **kwargs)
        log_auth_activity(
            'UNAUTHORIZED_ACCESS',
            request=request,
            user=request.user if request.user.is_authenticated else None,
            details='Non-Super Admin attempted to access the isolated Super Admin ecosystem.',
        )
        return HttpResponseForbidden('Access Denied: Super Admins only.')

    return wrapper


def today():
    return timezone.localdate()


def month_start(value=None):
    current = value or today()
    return current.replace(day=1)


def previous_month_window():
    current_start = month_start()
    previous_end = current_start - timedelta(days=1)
    previous_start = previous_end.replace(day=1)
    return previous_start, previous_end


def growth(current, previous):
    if previous:
        percent = round(((current - previous) / previous) * 100, 1)
    else:
        percent = 100.0 if current else 0.0
    if percent > 0:
        return percent, 'up'
    if percent < 0:
        return abs(percent), 'down'
    return 0.0, 'flat'


def kpi(title, value, icon, url, current=None, previous=None):
    current = value if current is None else current
    previous = 0 if previous is None else previous
    percent, trend = growth(current, previous)
    return {
        'title': title,
        'value': value,
        'icon': icon,
        'url': url,
        'growth': percent,
        'trend': trend,
        'previous': previous,
    }


def paginate(request, queryset, per_page=20):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def write_csv_response(file_name, headers, rows, request=None, report_name='Report'):
    SuperAdminExport.objects.create(
        report_name=report_name,
        export_format='csv',
        status='completed',
        requested_by=request.user if request and request.user.is_authenticated else None,
        file_name=file_name,
    )
    if request and request.user.is_authenticated:
        SuperAdminNotification.objects.create(
            title='Export Completed',
            message=f'{report_name} was exported successfully.',
            notification_type='EXPORT_COMPLETED',
            created_by=request.user,
        )
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{file_name}"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return response


def ensure_system_notifications(request):
    overdue = ManagementFollowUp.objects.filter(status='Pending', followup_date__lt=today()).count()
    if overdue and not SuperAdminNotification.objects.filter(
        notification_type='FOLLOWUP_OVERDUE',
        is_read=False,
        created_at__date=today(),
    ).exists():
        SuperAdminNotification.objects.create(
            title='Follow-up Overdue',
            message=f'{overdue} management follow-ups are overdue.',
            notification_type='FOLLOWUP_OVERDUE',
            created_by=request.user,
        )


def base_counts():
    today_date = today()
    current_start = month_start(today_date)
    previous_start, previous_end = previous_month_window()
    total_leads = Lead.objects.count()
    admissions = AdmissionSheet.objects.count()

    current_users = User.all_objects.filter(date_joined__date__gte=current_start).count()
    previous_users = User.all_objects.filter(date_joined__date__gte=previous_start, date_joined__date__lte=previous_end).count()
    current_leads = Lead.objects.filter(created_at__date__gte=current_start).count()
    previous_leads = Lead.objects.filter(created_at__date__gte=previous_start, created_at__date__lte=previous_end).count()
    monthly_admissions = AdmissionSheet.objects.filter(admission_date__gte=current_start).count()
    previous_admissions = AdmissionSheet.objects.filter(admission_date__gte=previous_start, admission_date__lte=previous_end).count()
    monthly_placements = PlacementOffer.objects.filter(created_at__date__gte=current_start).count()
    previous_placements = PlacementOffer.objects.filter(created_at__date__gte=previous_start, created_at__date__lte=previous_end).count()
    conversion_rate = round((admissions / total_leads) * 100, 1) if total_leads else 0

    return {
        'today': today_date,
        'current_start': current_start,
        'previous_start': previous_start,
        'previous_end': previous_end,
        'monthly_admissions': monthly_admissions,
        'monthly_placements': monthly_placements,
        'conversion_rate': conversion_rate,
        'kpis': [
            kpi('Total Active Users', User.all_objects.filter(is_active=True, is_deleted=False).exclude(role='SUPER_ADMIN').count(), 'bi-person-check', reverse('superadmin_user_performance'), current_users, previous_users),
            kpi('Total Candidates', Candidate.objects.count(), 'bi-briefcase', reverse('superadmin_hr_candidates')),
            kpi('Total Leads', total_leads, 'bi-funnel', reverse('superadmin_telecaller_leads'), current_leads, previous_leads),
            kpi("Today's Activities", AuthActivityLog.objects.filter(created_at__date=today_date).count() + LeadActivity.objects.filter(created_at__date=today_date).count() + CandidateActivity.objects.filter(created_at__date=today_date).count(), 'bi-activity', reverse('superadmin_activity_logs')),
            kpi('Monthly Admissions', monthly_admissions, 'bi-mortarboard', reverse('superadmin_counsellor_admissions'), monthly_admissions, previous_admissions),
            kpi('Monthly Placements', monthly_placements, 'bi-award', reverse('superadmin_hr_performance'), monthly_placements, previous_placements),
            kpi('Overall Conversion Rate', f'{conversion_rate}%', 'bi-graph-up-arrow', reverse('superadmin_reports'), admissions, total_leads),
            kpi('Pending Follow-ups', ManagementFollowUp.objects.filter(status='Pending').count() + HRFollowUp.objects.filter(completed=False).count(), 'bi-clock-history', reverse('superadmin_counsellor_followups')),
        ],
    }


def top_performers():
    return {
        'hr': User.all_objects.filter(role='hr').annotate(total=Count('hr_candidates')).order_by('-total', 'username')[:5],
        'counsellors': User.all_objects.filter(role='counselor').annotate(total=Count('counseling_sessions')).order_by('-total', 'username')[:5],
        'telecallers': User.all_objects.filter(role='telecaller').annotate(total=Count('created_call_logs')).order_by('-total', 'username')[:5],
    }


def dashboard_summaries():
    candidates = Candidate.objects.count()
    hr_conversions = Candidate.objects.filter(status__in=['selected', 'joined']).count()
    leads = Lead.objects.count()
    admissions = AdmissionSheet.objects.count()
    calls = CallLog.objects.count()
    interested = Lead.objects.filter(status='Interested').count()
    return [
        {
            'title': 'HR Summary',
            'url': reverse('superadmin_hr'),
            'icon': 'bi-briefcase',
            'metrics': [
                ('Total activities', CandidateActivity.objects.count()),
                ('Placements', PlacementOffer.objects.filter(joining_status='joined').count()),
                ('Interviews', HRInterview.objects.count() + PlacementInterview.objects.count()),
                ('Conversion rate', f'{round((hr_conversions / candidates) * 100, 1) if candidates else 0}%'),
                ('Pending tasks', HRFollowUp.objects.filter(completed=False).count()),
            ],
        },
        {
            'title': 'Counsellor Summary',
            'url': reverse('superadmin_counsellor'),
            'icon': 'bi-chat-dots',
            'metrics': [
                ('Admissions', admissions),
                ('Follow-ups', ManagementFollowUp.objects.count()),
                ('Conversion rate', f'{round((admissions / leads) * 100, 1) if leads else 0}%'),
                ('Sessions completed', CounselingSession.objects.count()),
                ('Pending follow-ups', ManagementFollowUp.objects.filter(status='Pending').count()),
            ],
        },
        {
            'title': 'Telecaller Summary',
            'url': reverse('superadmin_telecaller'),
            'icon': 'bi-telephone',
            'metrics': [
                ('Calls made', calls),
                ('Interested leads', interested),
                ('Appointments booked', VisitSheet.objects.count()),
                ('Lead qualification rate', f'{round((Lead.objects.filter(status="Qualified").count() / leads) * 100, 1) if leads else 0}%'),
                ('Pending follow-ups', ManagementFollowUp.objects.filter(status='Pending').count()),
            ],
        },
    ]


def department_comparison():
    rows = [
        {'department': 'HR', 'activities': CandidateActivity.objects.count(), 'conversions': Candidate.objects.filter(status__in=['selected', 'joined']).count()},
        {'department': 'Counsellor', 'activities': CounselingSession.objects.count() + ManagementFollowUp.objects.count(), 'conversions': AdmissionSheet.objects.count()},
        {'department': 'Telecaller', 'activities': CallLog.objects.count(), 'conversions': VisitSheet.objects.count() + Lead.objects.filter(status__in=['Interested', 'Qualified']).count()},
    ]
    max_activity = max([item['activities'] for item in rows] or [0])
    max_conversion = max([item['conversions'] for item in rows] or [0])
    for item in rows:
        productivity = round((item['activities'] / max_activity) * 100, 1) if max_activity else 0
        conversion = round((item['conversions'] / max_conversion) * 100, 1) if max_conversion else 0
        item['productivity'] = productivity
        item['performance_score'] = round((productivity + conversion) / 2, 1)
    return rows


@login_required
@super_admin_required
def dashboard(request):
    ensure_system_notifications(request)
    counts = base_counts()
    context = {
        **counts,
        'recent_logs': AuthActivityLog.objects.select_related('user')[:8],
        'recent_lead_activity': LeadActivity.objects.select_related('created_by', 'lead', 'lead__inquiry')[:6],
        'recent_candidate_activity': CandidateActivity.objects.select_related('created_by', 'candidate')[:6],
        'top_performers': top_performers(),
        'department_summaries': dashboard_summaries(),
        'department_comparison': department_comparison(),
        'growth_cards': [
            row('Leads Growth Trend', Lead.objects.filter(created_at__date__gte=counts['current_start']).count(), 'This month'),
            row('Admissions Growth Trend', counts['monthly_admissions'], 'This month'),
            row('Placement Growth Trend', counts['monthly_placements'], 'This month'),
        ],
        'notifications': SuperAdminNotification.objects.filter(is_read=False)[:8],
        'unread_count': SuperAdminNotification.objects.filter(is_read=False).count(),
    }
    return render(request, 'accounts/superadmin_dashboard.html', context)


@login_required
@super_admin_required
def users(request):
    users_qs = User.all_objects.exclude(role='SUPER_ADMIN').order_by('-date_joined')
    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    status = request.GET.get('status', '').strip()
    sort = request.GET.get('sort', '-date_joined')

    allowed_sorts = {'username', '-username', 'email', '-email', 'role', '-role', 'date_joined', '-date_joined'}
    if query:
        users_qs = users_qs.filter(Q(username__icontains=query) | Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query))
    if role:
        users_qs = users_qs.filter(role=role)
    if status == 'active':
        users_qs = users_qs.filter(is_active=True, is_deleted=False)
    elif status == 'inactive':
        users_qs = users_qs.filter(Q(is_active=False) | Q(is_deleted=True))
    if sort in allowed_sorts:
        users_qs = users_qs.order_by(sort)

    if request.GET.get('export') == 'csv':
        return write_csv_response(
            'superadmin-users.csv',
            ['ID', 'Username', 'Email', 'Role', 'Active', 'Deleted', 'Joined'],
            ((u.id, u.username, u.email, u.role, u.is_active, u.is_deleted, u.date_joined) for u in users_qs),
            request,
            'User Reports',
        )

    if request.method == 'POST':
        action = request.POST.get('bulk_action')
        ids = request.POST.getlist('selected_users')
        selected = User.all_objects.filter(id__in=ids).exclude(role='SUPER_ADMIN')
        if action == 'activate':
            selected.update(is_active=True, is_deleted=False, deleted_at=None)
        elif action in ('deactivate', 'block'):
            selected.update(is_active=False)
        elif action == 'delete':
            for user in selected:
                user.delete()
        messages.success(request, 'Bulk action completed.')
        return redirect('superadmin_users')

    return render(request, 'accounts/superadmin_users.html', {
        'page_obj': paginate(request, users_qs),
        'query': query,
        'role': role,
        'status': status,
        'sort': sort,
        'role_choices': [choice for choice in User.ROLE_CHOICES if choice[0] != 'SUPER_ADMIN'],
    })


@login_required
@super_admin_required
def user_create(request):
    if request.method == 'POST':
        form = SuperAdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            log_auth_activity('USER_CREATED', request=request, user=request.user, username=user.username, details=f'Created credentials for {user.get_role_display()}.')
            SuperAdminNotification.objects.create(title='New User Created', message=f'{user.username} was created as {user.get_role_display()}.', notification_type='USER_CREATED', created_by=request.user)
            messages.success(request, f'{user.get_role_display()} credentials created successfully.')
            return redirect('superadmin_user_detail', user_id=user.id)
    else:
        form = SuperAdminUserCreationForm()
    return render(request, 'accounts/superadmin_user_add.html', {'form': form})


@login_required
@super_admin_required
def user_detail(request, user_id):
    user_obj = get_object_or_404(User.all_objects.exclude(role='SUPER_ADMIN'), id=user_id)
    logs = AuthActivityLog.objects.filter(Q(user=user_obj) | Q(username__iexact=user_obj.username) | Q(username__iexact=user_obj.email))[:25]
    return render(request, 'accounts/superadmin_user_detail.html', {'user_obj': user_obj, 'logs': logs})


@login_required
@super_admin_required
def user_edit(request, user_id):
    user_obj = get_object_or_404(User.all_objects.exclude(role='SUPER_ADMIN'), id=user_id)
    if request.method == 'POST':
        form = SuperAdminUserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('superadmin_user_detail', user_id=user_obj.id)
    else:
        form = SuperAdminUserEditForm(instance=user_obj)
    return render(request, 'accounts/superadmin_user_edit.html', {'form': form, 'user_obj': user_obj})


@login_required
@super_admin_required
def user_reset_password(request, user_id):
    user_obj = get_object_or_404(User.all_objects.exclude(role='SUPER_ADMIN'), id=user_id)
    if request.method == 'POST':
        form = SuperAdminPasswordResetForm(request.POST)
        if form.is_valid():
            user_obj.set_password(form.cleaned_data['password1'])
            user_obj.save(update_fields=['password'])
            log_auth_activity('PASSWORD_RESET', request=request, user=request.user, username=user_obj.username, details='Password reset by Super Admin.')
            SuperAdminNotification.objects.create(title='Password Reset', message=f'Password was reset for {user_obj.username}.', notification_type='PASSWORD_RESET', created_by=request.user)
            messages.success(request, 'Password reset successfully.')
            return redirect('superadmin_user_detail', user_id=user_obj.id)
    else:
        form = SuperAdminPasswordResetForm()
    return render(request, 'accounts/superadmin_user_reset_password.html', {'form': form, 'user_obj': user_obj})


@login_required
@super_admin_required
def user_action(request, user_id, action):
    user_obj = get_object_or_404(User.all_objects.exclude(role='SUPER_ADMIN'), id=user_id)
    if action == 'activate':
        user_obj.is_active = True
        user_obj.is_deleted = False
        user_obj.deleted_at = None
        user_obj.save(update_fields=['is_active', 'is_deleted', 'deleted_at'])
    elif action in ('deactivate', 'block'):
        user_obj.is_active = False
        user_obj.save(update_fields=['is_active'])
    elif action == 'delete':
        user_obj.delete()
    else:
        return HttpResponseForbidden('Invalid user action.')
    messages.success(request, f'User {action} action completed.')
    return redirect('superadmin_users')


def analytics_context(module, page_title, kpis, chart_labels, chart_values, table_obj=None, table_title='Records'):
    max_value = max(chart_values) if chart_values else 0
    chart_pairs = [
        {'label': label, 'value': value, 'percent': round((value / max_value) * 100) if max_value else 0}
        for label, value in zip(chart_labels, chart_values)
    ]
    return {
        'module': module,
        'page_title': page_title,
        'kpis': kpis,
        'chart_labels': chart_labels,
        'chart_values': chart_values,
        'chart_pairs': chart_pairs,
        'table_obj': table_obj,
        'table_title': table_title,
    }


def status_chart(label, queryset, field, choices):
    return {
        'title': label,
        'labels': [display for _, display in choices],
        'values': [queryset.filter(**{field: value}).count() for value, _ in choices],
    }


def row(label, value, detail='', badge=''):
    return {'label': label, 'value': value, 'detail': detail, 'badge': badge}


def analytics_page(request, module, page_title, kpis, chart_title, chart_pairs, rows=None, table_title='Recent Records', actions=None):
    pairs = [{'label': label, 'value': value} for label, value in chart_pairs]
    max_value = max([item['value'] for item in pairs] or [0])
    for item in pairs:
        item['percent'] = round((item['value'] / max_value) * 100) if max_value else 0
    return render(request, 'accounts/superadmin_analytics.html', {
        'module': module,
        'page_title': page_title,
        'kpis': kpis,
        'chart_title': chart_title,
        'chart_pairs': pairs,
        'table_rows': rows or [],
        'table_title': table_title,
        'actions': actions or [],
    })


def user_performance_rows():
    rows = []
    users = User.all_objects.filter(role__in=['hr', 'counselor', 'telecaller']).order_by('role', 'username')
    for user in users:
        if user.role == 'hr':
            activities = CandidateActivity.objects.filter(created_by=user).count()
            conversions = Candidate.objects.filter(assigned_hr=user, status__in=['selected', 'joined']).count()
            total = Candidate.objects.filter(assigned_hr=user).count()
            department = 'HR'
        elif user.role == 'counselor':
            activities = CounselingSession.objects.filter(counselor=user).count() + ManagementFollowUp.objects.filter(created_by=user).count()
            conversions = AdmissionSheet.objects.filter(counselor=user).count()
            total = Lead.objects.filter(assigned_counselor=user).count()
            department = 'Counsellor'
        else:
            activities = CallLog.objects.filter(created_by=user).count()
            conversions = VisitSheet.objects.filter(created_by=user).count() + Lead.objects.filter(assigned_telecaller=user, status__in=['Interested', 'Qualified']).count()
            total = Lead.objects.filter(assigned_telecaller=user).count()
            department = 'Telecaller'
        conversion_rate = round((conversions / total) * 100, 1) if total else 0
        score = min(100, round((activities * 2) + conversion_rate, 1))
        rows.append({
            'user': user,
            'department': department,
            'activities': activities,
            'conversion_rate': conversion_rate,
            'score': score,
        })
    rows.sort(key=lambda item: item['score'], reverse=True)
    for index, item in enumerate(rows, 1):
        item['rank'] = index
    return rows


@login_required
@super_admin_required
def hr_dashboard(request):
    total = Candidate.objects.count()
    joined = Candidate.objects.filter(status='joined').count()
    kpis = [
        kpi('Total Candidates', total, 'bi-briefcase', reverse('superadmin_hr_candidates')),
        kpi('Interviews Scheduled', HRInterview.objects.count() + PlacementInterview.objects.count(), 'bi-calendar-check', reverse('superadmin_hr_interviews')),
        kpi('Interviews Conducted', HRInterview.objects.exclude(decision='pending').count(), 'bi-person-check', reverse('superadmin_hr_interviews')),
        kpi('Shortlisted', Candidate.objects.filter(status='selected').count(), 'bi-check2-circle', reverse('superadmin_hr_candidates') + '?status=selected'),
        kpi('Rejected', Candidate.objects.filter(status='rejected').count(), 'bi-x-circle', reverse('superadmin_hr_candidates') + '?status=rejected'),
        kpi('Offer Sent', PlacementOffer.objects.exclude(offer_status='pending').count(), 'bi-envelope-check', reverse('superadmin_hr_performance')),
        kpi('Joined Candidates', joined, 'bi-award', reverse('superadmin_hr_candidates') + '?status=joined'),
        kpi('Placement Rate', f'{round((joined / total) * 100, 1) if total else 0}%', 'bi-graph-up', reverse('superadmin_hr_performance')),
    ]
    leaders = top_performers()['hr']
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('hr', 'HR Analytics', kpis, ['New', 'Interview', 'Selected', 'Joined'], [Candidate.objects.filter(status='new').count(), Candidate.objects.filter(status='interview_scheduled').count(), Candidate.objects.filter(status='selected').count(), joined], leaders, 'Top HR Leaderboard'))


@login_required
@super_admin_required
def hr_recruitment(request):
    candidates = Candidate.objects.select_related('assigned_hr').order_by('-updated_at')
    total = candidates.count()
    selected = candidates.filter(status='selected').count()
    joined = candidates.filter(status='joined').count()
    conducted = HRInterview.objects.exclude(decision='pending').count()
    chart = status_chart('Candidate Status Distribution', candidates, 'status', Candidate.STATUS_CHOICES)
    rows = [
        row(candidate.full_name, candidate.applying_position, candidate.assigned_hr.username if candidate.assigned_hr else 'Unassigned', candidate.get_status_display())
        for candidate in candidates[:8]
    ]
    kpis = [
        kpi('Total Candidates', total, 'bi-briefcase', reverse('superadmin_hr_candidates')),
        kpi('Interviews Scheduled', HRInterview.objects.count(), 'bi-calendar-check', reverse('superadmin_hr_interviews')),
        kpi('Interviews Conducted', conducted, 'bi-person-check', reverse('superadmin_hr_interviews')),
        kpi('Selected', selected, 'bi-check2-circle', reverse('superadmin_hr_candidates') + '?status=selected'),
        kpi('Rejected', candidates.filter(status='rejected').count(), 'bi-x-circle', reverse('superadmin_hr_candidates') + '?status=rejected'),
        kpi('Joined', joined, 'bi-award', reverse('superadmin_hr_candidates') + '?status=joined'),
        kpi('Conversion Rate', f'{round((joined / total) * 100, 1) if total else 0}%', 'bi-graph-up', reverse('superadmin_hr_performance'), joined, total),
    ]
    return analytics_page(request, 'hr', 'Recruitment Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Candidates')


@login_required
@super_admin_required
def hr_placement(request):
    assignments = PlacementStudentAssignment.objects.select_related('company', 'drive').order_by('-assigned_at')
    total = assignments.count()
    placed = assignments.filter(final_status='joined').count()
    rows = [
        row(item.company.name if item.company else 'No company', item.drive.job_role if item.drive else item.display_name, f'Selected: {item.final_status}', item.interview_status)
        for item in assignments[:8]
    ]
    chart = status_chart('Placement Funnel', assignments, 'final_status', PlacementStudentAssignment.FINAL_STATUS_CHOICES)
    kpis = [
        kpi('Companies', PlacementCompany.objects.count(), 'bi-buildings', reverse('superadmin_hr_placement')),
        kpi('Placement Drives', PlacementDrive.objects.count(), 'bi-calendar2-week', reverse('superadmin_hr_placement')),
        kpi('Eligible Employees', total, 'bi-people', reverse('superadmin_hr_placement')),
        kpi('Selected Candidates', assignments.filter(final_status__in=['selected', 'joined']).count(), 'bi-check2-circle', reverse('superadmin_hr_placement')),
        kpi('Placed Candidates', placed, 'bi-award', reverse('superadmin_hr_placement')),
        kpi('Placement Rate', f'{round((placed / total) * 100, 1) if total else 0}%', 'bi-graph-up-arrow', reverse('superadmin_hr_performance'), placed, total),
    ]
    return analytics_page(request, 'hr', 'Placement Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Drive Performance')


@login_required
@super_admin_required
def hr_project(request):
    assignments = ProjectEmployeeAssignment.objects.select_related('company', 'drive').order_by('-assigned_at')
    total = assignments.count()
    allocated = assignments.filter(final_status='allocated').count()
    rows = [
        row(item.company.name if item.company else 'No company', item.drive.project_name if item.drive else item.display_name, f'Released: {item.final_status == "released"}', item.interview_status)
        for item in assignments[:8]
    ]
    chart = status_chart('Project Distribution', assignments, 'final_status', ProjectEmployeeAssignment.FINAL_STATUS_CHOICES)
    kpis = [
        kpi('Projects', ProjectDrive.objects.count(), 'bi-kanban', reverse('superadmin_hr_project')),
        kpi('Employees Assigned', total, 'bi-people', reverse('superadmin_hr_project')),
        kpi('Allocations', ProjectAllocation.objects.filter(allocation_status='allocated').count(), 'bi-diagram-3', reverse('superadmin_hr_project')),
        kpi('Released Employees', assignments.filter(final_status='released').count(), 'bi-box-arrow-right', reverse('superadmin_hr_project')),
        kpi('Allocation Rate', f'{round((allocated / total) * 100, 1) if total else 0}%', 'bi-graph-up', reverse('superadmin_hr_project'), allocated, total),
    ]
    return analytics_page(request, 'hr', 'Project HR Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Project Resource Utilization')


@login_required
@super_admin_required
def hr_external(request):
    employees = ExternalEmployee.objects.all()
    attendance = ExternalAttendanceLog.objects.select_related('employee').order_by('-date')
    total_logs = attendance.count()
    present = attendance.filter(status='present').count()
    chart = status_chart('Attendance Distribution', attendance, 'status', ExternalAttendanceLog.STATUS_CHOICES)
    rows = [
        row(item.employee.full_name, item.employee.department or item.employee.branch, item.date.strftime('%d %b %Y'), item.get_status_display())
        for item in attendance[:8]
    ]
    kpis = [
        kpi('Total Employees', employees.count(), 'bi-people', reverse('superadmin_hr_external')),
        kpi('Present', present, 'bi-person-check', reverse('superadmin_hr_external')),
        kpi('Absent', attendance.filter(status='absent').count(), 'bi-person-x', reverse('superadmin_hr_external')),
        kpi('Leave Count', attendance.filter(status='leave').count(), 'bi-calendar-minus', reverse('superadmin_hr_external')),
        kpi('Attendance Percentage', f'{round((present / total_logs) * 100, 1) if total_logs else 0}%', 'bi-percent', reverse('superadmin_hr_external'), present, total_logs),
    ]
    return analytics_page(request, 'hr', 'External HR Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Attendance')


@login_required
@super_admin_required
def hr_reports(request):
    return reports(request)


@login_required
@super_admin_required
def hr_candidates(request):
    qs = Candidate.objects.select_related('assigned_hr').order_by('-updated_at')
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    if query:
        qs = qs.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(mobile__icontains=query) | Q(applying_position__icontains=query))
    if status:
        qs = qs.filter(status=status)
    if request.GET.get('export') == 'csv':
        return write_csv_response('hr-candidates.csv', ['Name', 'Email', 'Mobile', 'Position', 'Status', 'Assigned HR'], ((c.full_name, c.email, c.mobile, c.applying_position, c.status, c.assigned_hr) for c in qs), request, 'HR Candidates')
    return render(request, 'accounts/superadmin_candidate_table.html', {'page_obj': paginate(request, qs), 'query': query, 'status': status, 'status_choices': Candidate.STATUS_CHOICES})


@login_required
@super_admin_required
def hr_interviews(request):
    qs = HRInterview.objects.select_related('candidate', 'scheduled_by').order_by('-date', '-time')
    return render(request, 'accounts/superadmin_simple_table.html', {'title': 'HR Interviews', 'page_obj': paginate(request, qs), 'columns': ['Candidate', 'Date', 'Interviewer', 'Decision'], 'kind': 'interviews'})


@login_required
@super_admin_required
def hr_performance(request):
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('hr', 'HR Performance', [], ['Scheduled', 'Conducted', 'Selected', 'Joined'], [HRInterview.objects.count(), HRInterview.objects.exclude(decision='pending').count(), Candidate.objects.filter(status='selected').count(), Candidate.objects.filter(status='joined').count()], top_performers()['hr'], 'Top HR Leaderboard'))


@login_required
@super_admin_required
def counsellor_dashboard(request):
    assigned = Lead.objects.filter(assigned_counselor__isnull=False).count()
    admissions = AdmissionSheet.objects.count()
    kpis = [
        kpi('Leads Assigned', assigned, 'bi-people', reverse('superadmin_counsellor')),
        kpi('Sessions Conducted', CounselingSession.objects.count(), 'bi-chat-dots', reverse('superadmin_counsellor_performance')),
        kpi('Admissions Done', admissions, 'bi-mortarboard', reverse('superadmin_counsellor_admissions')),
        kpi('Follow-ups Pending', ManagementFollowUp.objects.filter(status='Pending').count(), 'bi-clock', reverse('superadmin_counsellor_followups')),
        kpi('Conversion Rate', f'{round((admissions / assigned) * 100, 1) if assigned else 0}%', 'bi-graph-up', reverse('superadmin_counsellor_performance')),
    ]
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('counsellor', 'Counsellor Analytics', kpis, ['Assigned', 'Sessions', 'Admissions', 'Pending Follow-ups'], [assigned, CounselingSession.objects.count(), admissions, ManagementFollowUp.objects.filter(status='Pending').count()], top_performers()['counsellors'], 'Top Counsellors'))


@login_required
@super_admin_required
def counsellor_leads(request):
    leads = Lead.objects.select_related('inquiry', 'assigned_counselor').order_by('-updated_at')
    assigned = leads.filter(assigned_counselor__isnull=False).count()
    converted = leads.filter(counselor_status='CONVERTED').count()
    chart = status_chart('Lead Status Distribution', leads, 'counselor_status', Lead.COUNSELOR_STATUS_CHOICES)
    rows = [
        row(lead.inquiry.full_name, lead.inquiry.course_interest, lead.assigned_counselor.username if lead.assigned_counselor else 'Unassigned', lead.get_counselor_status_display())
        for lead in leads[:8]
    ]
    kpis = [
        kpi('Assigned Leads', assigned, 'bi-person-lines-fill', reverse('superadmin_counsellor_leads')),
        kpi('New Leads', leads.filter(counselor_status='NEW').count(), 'bi-stars', reverse('superadmin_counsellor_leads')),
        kpi('Active Leads', leads.exclude(counselor_status__in=['CONVERTED', 'LOST', 'NOT_INTERESTED']).count(), 'bi-lightning', reverse('superadmin_counsellor_leads')),
        kpi('Converted Leads', converted, 'bi-check2-circle', reverse('superadmin_counsellor_admissions')),
        kpi('Conversion Rate', f'{round((converted / assigned) * 100, 1) if assigned else 0}%', 'bi-graph-up', reverse('superadmin_counsellor_performance'), converted, assigned),
    ]
    return analytics_page(request, 'counsellor', 'Lead Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Counsellor Lead Snapshot')


@login_required
@super_admin_required
def counsellor_sessions(request):
    sessions = CounselingSession.objects.select_related('lead', 'lead__inquiry', 'counselor').order_by('-session_date')
    visits = VisitSheet.objects.all()
    rows = [
        row(session.lead.inquiry.full_name, session.next_action or 'Session completed', session.counselor.username, session.session_date.strftime('%d %b %Y'))
        for session in sessions[:8]
    ]
    kpis = [
        kpi('Sessions Conducted', sessions.count(), 'bi-chat-square-dots', reverse('superadmin_counsellor_sessions')),
        kpi('Visits Scheduled', visits.filter(status='Scheduled').count(), 'bi-calendar-event', reverse('superadmin_telecaller_appointments')),
        kpi('Visits Completed', visits.filter(status__in=['Visited', 'Admission Done']).count(), 'bi-calendar-check', reverse('superadmin_telecaller_appointments')),
    ]
    chart_pairs = [
        ('Sessions', sessions.count()),
        ('Scheduled Visits', visits.filter(status='Scheduled').count()),
        ('Completed Visits', visits.filter(status__in=['Visited', 'Admission Done']).count()),
    ]
    return analytics_page(request, 'counsellor', 'Session Analytics', kpis, 'Session and Visit Trend', chart_pairs, rows, 'Recent Sessions')


@login_required
@super_admin_required
def counsellor_followups(request):
    qs = ManagementFollowUp.objects.select_related('lead', 'lead__inquiry', 'created_by').order_by('-created_at')
    return render(request, 'accounts/superadmin_simple_table.html', {'title': 'Counsellor Follow-ups', 'page_obj': paginate(request, qs), 'columns': ['Lead', 'Date', 'Status', 'Owner'], 'kind': 'followups'})


@login_required
@super_admin_required
def counsellor_followup_analytics(request):
    followups = ManagementFollowUp.objects.select_related('lead', 'lead__inquiry', 'created_by').order_by('-followup_date')
    pending = followups.filter(status='Pending').count()
    completed = followups.filter(status='Completed').count()
    overdue = followups.filter(status='Pending', followup_date__lt=today()).count()
    chart = status_chart('Follow-up Status Distribution', followups, 'status', ManagementFollowUp.STATUS_CHOICES)
    rows = [
        row(item.lead.inquiry.full_name, item.response[:80] if item.response else 'No response recorded', item.created_by.username if item.created_by else 'Unassigned', item.status)
        for item in followups[:8]
    ]
    kpis = [
        kpi('Pending Follow-ups', pending, 'bi-clock-history', reverse('superadmin_counsellor_followups')),
        kpi('Completed Follow-ups', completed, 'bi-check2-circle', reverse('superadmin_counsellor_followups')),
        kpi('Overdue Follow-ups', overdue, 'bi-exclamation-triangle', reverse('superadmin_counsellor_followups')),
    ]
    return analytics_page(request, 'counsellor', 'Follow-up Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Follow-ups')


@login_required
@super_admin_required
def counsellor_admissions(request):
    qs = AdmissionSheet.objects.select_related('counselor', 'lead').order_by('-admission_date')
    return render(request, 'accounts/superadmin_simple_table.html', {'title': 'Admissions', 'page_obj': paginate(request, qs), 'columns': ['Student', 'Admission No', 'Status', 'Counsellor'], 'kind': 'admissions'})


@login_required
@super_admin_required
def counsellor_admission_analytics(request):
    admissions = AdmissionSheet.objects.select_related('counselor').order_by('-admission_date')
    total_leads = Lead.objects.filter(assigned_counselor__isnull=False).count()
    confirmed = admissions.filter(admission_status='CONFIRMED').count()
    chart = status_chart('Admission Funnel', admissions, 'admission_status', AdmissionSheet.ADMISSION_STATUS_CHOICES)
    rows = [
        row(admission.student_name, admission.course_name, admission.counselor.username if admission.counselor else 'Unassigned', admission.get_admission_status_display())
        for admission in admissions[:8]
    ]
    kpis = [
        kpi('Admissions Confirmed', confirmed, 'bi-mortarboard', reverse('superadmin_counsellor_admissions')),
        kpi('Admissions Pending', admissions.filter(admission_status='PENDING').count(), 'bi-hourglass-split', reverse('superadmin_counsellor_admissions')),
        kpi('Conversion Rate', f'{round((confirmed / total_leads) * 100, 1) if total_leads else 0}%', 'bi-graph-up-arrow', reverse('superadmin_counsellor_performance'), confirmed, total_leads),
    ]
    return analytics_page(request, 'counsellor', 'Admission Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Admissions')


@login_required
@super_admin_required
def counsellor_performance(request):
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('counsellor', 'Counsellor Performance', [], ['Sessions', 'Visits', 'Admissions'], [CounselingSession.objects.count(), VisitSheet.objects.count(), AdmissionSheet.objects.count()], top_performers()['counsellors'], 'Counsellor Comparison'))


@login_required
@super_admin_required
def counsellor_reports(request):
    return reports(request)


@login_required
@super_admin_required
def telecaller_dashboard(request):
    total_calls = CallLog.objects.count()
    kpis = [
        kpi('Total Calls', total_calls, 'bi-telephone', reverse('superadmin_telecaller_calls')),
        kpi('Connected Calls', CallLog.objects.filter(call_status='Connected').count(), 'bi-telephone-inbound', reverse('superadmin_telecaller_calls') + '?status=Connected'),
        kpi('Unanswered Calls', CallLog.objects.exclude(call_status='Connected').count(), 'bi-telephone-x', reverse('superadmin_telecaller_calls')),
        kpi('Interested Leads', Lead.objects.filter(status='Interested').count(), 'bi-heart', reverse('superadmin_telecaller')),
        kpi('Appointments Booked', VisitSheet.objects.count(), 'bi-calendar-event', reverse('superadmin_telecaller_appointments')),
        kpi('Average Call Duration', round(CallLog.objects.aggregate(avg=Avg('call_duration'))['avg'] or 0, 1), 'bi-stopwatch', reverse('superadmin_telecaller_performance')),
    ]
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('telecaller', 'Telecaller Analytics', kpis, ['Connected', 'Not Answered', 'Busy', 'Invalid'], [CallLog.objects.filter(call_status='Connected').count(), CallLog.objects.filter(call_status='Not Answered').count(), CallLog.objects.filter(call_status='Busy').count(), CallLog.objects.filter(call_status='Invalid Number').count()], top_performers()['telecallers'], 'Telecaller Leaderboard'))


@login_required
@super_admin_required
def telecaller_leads(request):
    leads = Lead.objects.select_related('inquiry', 'assigned_telecaller').order_by('-updated_at')
    total = leads.count()
    interested = leads.filter(status='Interested').count()
    qualified = leads.filter(status='Qualified').count()
    chart = status_chart('Lead Funnel', leads, 'status', Lead.STATUS_CHOICES)
    rows = [
        row(lead.inquiry.full_name, lead.inquiry.mobile_number, lead.assigned_telecaller.username if lead.assigned_telecaller else 'Unassigned', lead.status)
        for lead in leads[:8]
    ]
    kpis = [
        kpi('Total Leads', total, 'bi-funnel', reverse('superadmin_telecaller_leads')),
        kpi('Interested Leads', interested, 'bi-heart', reverse('superadmin_telecaller_leads')),
        kpi('Qualified Leads', qualified, 'bi-check2-circle', reverse('superadmin_telecaller_leads')),
        kpi('Lead Qualification Rate', f'{round((qualified / total) * 100, 1) if total else 0}%', 'bi-graph-up', reverse('superadmin_telecaller_performance'), qualified, total),
    ]
    return analytics_page(request, 'telecaller', 'Lead Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Telecaller Lead Snapshot')


@login_required
@super_admin_required
def telecaller_calls(request):
    qs = CallLog.objects.select_related('lead', 'lead__inquiry', 'created_by').order_by('-call_date')
    return render(request, 'accounts/superadmin_simple_table.html', {'title': 'Telecaller Calls', 'page_obj': paginate(request, qs), 'columns': ['Lead', 'Status', 'Duration', 'Telecaller'], 'kind': 'calls'})


@login_required
@super_admin_required
def telecaller_call_analytics(request):
    calls = CallLog.objects.select_related('lead', 'lead__inquiry', 'created_by').order_by('-call_date')
    chart = status_chart('Call Status Distribution', calls, 'call_status', CallLog.STATUS_CHOICES)
    rows = [
        row(item.lead.inquiry.full_name, f'{item.call_duration}s', item.created_by.username if item.created_by else 'Unassigned', item.call_status)
        for item in calls[:8]
    ]
    kpis = [
        kpi('Connected Calls', calls.filter(call_status='Connected').count(), 'bi-telephone-inbound', reverse('superadmin_telecaller_calls')),
        kpi('Missed Calls', calls.filter(call_status='Not Answered').count(), 'bi-telephone-x', reverse('superadmin_telecaller_calls')),
        kpi('Busy Calls', calls.filter(call_status='Busy').count(), 'bi-telephone-minus', reverse('superadmin_telecaller_calls')),
        kpi('Unanswered Calls', calls.exclude(call_status='Connected').count(), 'bi-question-circle', reverse('superadmin_telecaller_calls')),
    ]
    return analytics_page(request, 'telecaller', 'Call Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Calls')


@login_required
@super_admin_required
def telecaller_appointments(request):
    qs = VisitSheet.objects.select_related('lead', 'lead__inquiry', 'counselor').order_by('-visit_date', '-visit_time')
    return render(request, 'accounts/superadmin_simple_table.html', {'title': 'Appointments', 'page_obj': paginate(request, qs), 'columns': ['Lead', 'Date', 'Status', 'Counsellor'], 'kind': 'appointments'})


@login_required
@super_admin_required
def telecaller_appointment_analytics(request):
    visits = VisitSheet.objects.select_related('lead', 'lead__inquiry', 'counselor').order_by('-visit_date', '-visit_time')
    booked = visits.count()
    completed = visits.filter(status__in=['Visited', 'Admission Done']).count()
    chart = status_chart('Appointment Funnel', visits, 'status', VisitSheet.STATUS_CHOICES)
    rows = [
        row(item.lead.inquiry.full_name, item.visit_date.strftime('%d %b %Y'), item.counselor.username if item.counselor else 'Unassigned', item.get_status_display())
        for item in visits[:8]
    ]
    kpis = [
        kpi('Appointments Booked', booked, 'bi-calendar-event', reverse('superadmin_telecaller_appointments')),
        kpi('Appointments Completed', completed, 'bi-calendar-check', reverse('superadmin_telecaller_appointments')),
        kpi('Conversion Percentage', f'{round((completed / booked) * 100, 1) if booked else 0}%', 'bi-percent', reverse('superadmin_telecaller_performance'), completed, booked),
    ]
    return analytics_page(request, 'telecaller', 'Appointment Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Appointments')


@login_required
@super_admin_required
def telecaller_followup_analytics(request):
    followups = ManagementFollowUp.objects.select_related('lead', 'lead__inquiry', 'created_by').order_by('-followup_date')
    pending = followups.filter(status='Pending').count()
    completed = followups.filter(status='Completed').count()
    overdue = followups.filter(status='Pending', followup_date__lt=today()).count()
    chart = status_chart('Status Distribution', followups, 'status', ManagementFollowUp.STATUS_CHOICES)
    rows = [
        row(item.lead.inquiry.full_name, item.followup_date.strftime('%d %b %Y'), item.created_by.username if item.created_by else 'Unassigned', item.status)
        for item in followups[:8]
    ]
    kpis = [
        kpi('Pending Follow-ups', pending, 'bi-clock-history', reverse('superadmin_counsellor_followups')),
        kpi('Completed Follow-ups', completed, 'bi-check2-circle', reverse('superadmin_counsellor_followups')),
        kpi('Overdue Follow-ups', overdue, 'bi-exclamation-triangle', reverse('superadmin_counsellor_followups')),
    ]
    return analytics_page(request, 'telecaller', 'Follow-up Analytics', kpis, chart['title'], zip(chart['labels'], chart['values']), rows, 'Recent Follow-ups')


@login_required
@super_admin_required
def telecaller_performance(request):
    return render(request, 'accounts/superadmin_analytics.html', analytics_context('telecaller', 'Telecaller Performance', [], ['Calls', 'Connected', 'Interested'], [CallLog.objects.count(), CallLog.objects.filter(call_status='Connected').count(), Lead.objects.filter(status='Interested').count()], top_performers()['telecallers'], 'Team Comparison'))


@login_required
@super_admin_required
def telecaller_reports(request):
    return reports(request)


@login_required
@super_admin_required
def user_performance(request):
    rows = user_performance_rows()
    query = request.GET.get('q', '').strip().lower()
    department = request.GET.get('department', '').strip().lower()
    if query:
        rows = [
            item for item in rows
            if query in item['user'].username.lower()
            or query in (item['user'].email or '').lower()
            or query in item['department'].lower()
        ]
    if department:
        rows = [item for item in rows if item['department'].lower() == department]
    return render(request, 'accounts/superadmin_user_performance.html', {
        'page_obj': paginate(request, rows, 25),
        'query': query,
        'department': department,
        'departments': ['HR', 'Counsellor', 'Telecaller'],
    })


@login_required
@super_admin_required
def reports(request):
    if request.GET.get('export') == 'csv':
        return write_csv_response('superadmin-reports.csv', ['Report', 'Count'], [('Users', User.all_objects.count()), ('Leads', Lead.objects.count()), ('Candidates', Candidate.objects.count()), ('Activities', AuthActivityLog.objects.count())], request, 'Performance Reports')
    return render(request, 'accounts/superadmin_reports.html', {'counts': base_counts(), 'top_performers': top_performers()})


@login_required
@super_admin_required
def exports(request):
    if request.GET.get('download'):
        report = request.GET.get('download')
        return write_csv_response(f'{report}.csv', ['Metric', 'Value'], [('Users', User.all_objects.count()), ('Leads', Lead.objects.count()), ('Candidates', Candidate.objects.count())], request, report.replace('-', ' ').title())
    return render(request, 'accounts/superadmin_exports.html', {'exports': SuperAdminExport.objects.select_related('requested_by')[:50]})


@login_required
@super_admin_required
def notifications(request):
    ensure_system_notifications(request)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_all_read':
            SuperAdminNotification.objects.update(is_read=True)
        elif action == 'delete':
            SuperAdminNotification.objects.filter(id=request.POST.get('notification_id')).delete()
        return redirect('superadmin_notifications')
    return render(request, 'accounts/superadmin_notifications.html', {'notifications': paginate(request, SuperAdminNotification.objects.select_related('created_by'), 25), 'unread_count': SuperAdminNotification.objects.filter(is_read=False).count()})


@login_required
@super_admin_required
def activity_logs(request):
    logs = AuthActivityLog.objects.select_related('user').order_by('-created_at')
    query = request.GET.get('q', '').strip()
    event = request.GET.get('event', '').strip()
    if query:
        logs = logs.filter(Q(username__icontains=query) | Q(details__icontains=query) | Q(path__icontains=query) | Q(ip_address__icontains=query))
    if event:
        logs = logs.filter(event_type=event)
    if request.GET.get('export') == 'csv':
        return write_csv_response('activity-logs.csv', ['Event', 'Username', 'IP', 'Path', 'Details', 'Time'], ((log.event_type, log.username, log.ip_address, log.path, log.details, log.created_at) for log in logs), request, 'Activity Reports')
    return render(request, 'accounts/superadmin_activity_logs.html', {'page_obj': paginate(request, logs, 25), 'query': query, 'event': event, 'event_choices': AuthActivityLog.EVENT_CHOICES})


@login_required
@super_admin_required
def settings(request):
    if request.method == 'POST':
        messages.success(request, 'Settings reviewed. Persistent policy storage can be connected when configuration storage is approved.')
        return redirect('superadmin_settings')
    return render(request, 'accounts/superadmin_settings.html')


@login_required
@super_admin_required
def global_search(request):
    query = request.GET.get('q', '').strip()
    context = {'query': query, 'users': [], 'candidates': [], 'leads': [], 'inquiries': []}
    if query:
        context['users'] = User.all_objects.filter(Q(username__icontains=query) | Q(email__icontains=query)).exclude(role='SUPER_ADMIN')[:10]
        context['candidates'] = Candidate.objects.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(mobile__icontains=query))[:10]
        context['leads'] = Lead.objects.select_related('inquiry').filter(Q(inquiry__full_name__icontains=query) | Q(inquiry__email__icontains=query) | Q(inquiry__mobile_number__icontains=query))[:10]
        context['inquiries'] = Inquiry.objects.filter(Q(full_name__icontains=query) | Q(email__icontains=query) | Q(mobile_number__icontains=query))[:10]
    return render(request, 'accounts/superadmin_search.html', context)
