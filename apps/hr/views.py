import csv
import io
import re
from collections import OrderedDict
from datetime import datetime, timedelta
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator
import base64
from io import BytesIO
from PIL import Image
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

from apps.accounts.models import User
from apps.accounts.auth_logging import log_auth_activity
from .forms import (
    CANDIDATE_DASHBOARD_STATUS_CHOICES,
    CandidateBasicForm,
    CandidateDocumentsForm,
    CandidateImportForm,
    CandidateNoteForm,
    CandidateProfessionalForm,
    CandidateQuickForm,
    CandidateRecruitmentForm,
    CandidateStatusForm,
    ExternalAttendanceForm,
    ExternalEmployeeForm,
    FollowUpForm,
    HRSignupForm,
    InterviewFeedbackForm,
    InterviewForm,
    PlacementAssignmentForm,
    PlacementBatchForm,
    PlacementBatchImportForm,
    PlacementCompanyForm,
    PlacementDriveForm,
    EmailConfigurationForm,
    PlacementEmailForm,
    PlacementInterviewForm,
    PlacementOfferForm,
    ProjectAllocationForm,
    ProjectAssignmentForm,
    ProjectCompanyForm,
    ProjectDriveForm,
    ProjectInterviewForm,
)
from apps.students.models import StudentAdmission, StudentProfile
from .models import (
    Candidate,
    CandidateActivity,
    ExternalAttendanceLog,
    EmailConfiguration,
    ExternalEmployee,
    FollowUp,
    Interview,
    PlacementActivity,
    PlacementBatch,
    PlacementBatchImport,
    PlacementBatchStudent,
    PlacementCompany,
    PlacementDrive,
    PlacementEmailLog,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
    ProjectActivity,
    ProjectAllocation,
    ProjectCompany,
    ProjectDrive,
    ProjectEmployeeAssignment,
    ProjectInterview,
)
from .attendance_automation import attendance_values, employee_for_user
from .email_services import EmailConfigurationService, EmailDeliveryError

EXTERNAL_BRANCHES = {
    'thane': {'slug': 'thane', 'name': 'Dcodetech Thane'},
    'nashik': {'slug': 'nashik', 'name': 'Dcodetech Nashik'},
}


def hr_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'hr':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: HR only.")

    return wrapper


def signup_hr(request):
    log_auth_activity(
        'REGISTRATION_BLOCKED',
        request=request,
        username=request.POST.get('username', ''),
        details='Public HR registration endpoint was accessed.',
    )
    return HttpResponseForbidden('Public registration is disabled. Please contact the Super Admin for credentials.')


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
    
    model = queryset.model
    field_names = [f.name for f in model._meta.get_fields()]
    
    q_objects = Q()
    owner_fields = ['assigned_hr', 'created_by', 'handled_by', 'scheduled_by', 'assigned_by', 'marked_by']
    
    added = False
    for field in owner_fields:
        if field in field_names:
            q_objects |= Q(**{field: request.user})
            added = True
            
    if added:
        return queryset.filter(q_objects).distinct()
    
    return queryset


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
    followups = hr_scope(FollowUp.objects.filter(candidate__in=candidates), request)
    interviews = hr_scope(Interview.objects.filter(candidate__in=candidates), request)

    def metric(label, icon, color, value, current_filter, previous_filter, url=''):
        current = candidates.filter(current_filter).count() if current_filter else value
        previous = candidates.filter(previous_filter).count() if previous_filter else 0
        return {
            'label': label,
            'icon': icon,
            'color': color,
            'value': value,
            'url': url,
            'trend': trend_label(current, previous),
            'spark': [max(8, min(100, value % 70 + 20)), max(8, min(100, current % 80 + 15)), max(8, min(100, (previous + value) % 90 + 10))],
        }

    interviews_current = interviews.filter(created_at__date__gte=month_start).count()
    interviews_previous = interviews.filter(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end).count()
    pending_followups = followups.filter(completed=False, follow_up_date__gte=today).count()
    candidate_list_url = reverse('hr:candidate_list')

    return [
        metric('Total Candidates', 'bi-people-fill', 'indigo', candidates.count(), Q(created_at__date__gte=month_start), Q(created_at__date__gte=prev_month_start, created_at__date__lte=prev_month_end), candidate_list_url),
        metric('Applied', 'bi-person-plus-fill', 'violet', candidates.filter(status='new').count(), Q(status='new', updated_at__date__gte=month_start), Q(status='new', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=new'),
        metric('Interviews Scheduled', 'bi-calendar-check-fill', 'blue', candidates.filter(status='interview_scheduled').count(), Q(status='interview_scheduled', updated_at__date__gte=month_start), Q(status='interview_scheduled', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=interview_scheduled'),
        metric('Selected', 'bi-patch-check-fill', 'orange', candidates.filter(status='selected').count(), Q(status='selected', updated_at__date__gte=month_start), Q(status='selected', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=selected'),
        metric('Rejected', 'bi-x-octagon-fill', 'red', candidates.filter(status='rejected').count(), Q(status='rejected', updated_at__date__gte=month_start), Q(status='rejected', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=rejected'),
        metric('Joined', 'bi-person-check-fill', 'teal', candidates.filter(status='joined').count(), Q(status='joined', updated_at__date__gte=month_start), Q(status='joined', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=joined'),
        metric('On Hold', 'bi-pause-circle-fill', 'amber', candidates.filter(status='on_hold').count(), Q(status='on_hold', updated_at__date__gte=month_start), Q(status='on_hold', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=on_hold'),
        metric('Pending Follow-ups', 'bi-clock-fill', 'amber', candidates.filter(status='follow_up_pending').count(), Q(status='follow_up_pending', updated_at__date__gte=month_start), Q(status='follow_up_pending', updated_at__date__gte=prev_month_start, updated_at__date__lte=prev_month_end), f'{candidate_list_url}?status=follow_up_pending'),
    ]


def candidate_queryset(request):
    qs = hr_scope(Candidate.objects.select_related('assigned_hr'), request)
    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    source = request.GET.get('source', '').strip()
    added = request.GET.get('added', '').strip()
    added_from = request.GET.get('added_from', '').strip()
    added_to = request.GET.get('added_to', '').strip()

    if query:
        qs = qs.filter(
            Q(full_name__icontains=query)
            | Q(mobile__icontains=query)
            | Q(email__icontains=query)
            | Q(applying_position__icontains=query)
            | Q(location__icontains=query)
            | Q(remarks__icontains=query)
        )
    if status:
        qs = qs.filter(status=status)
    if source:
        qs = qs.filter(source=source)
    today = timezone.localdate()
    if added == 'today':
        qs = qs.filter(date_added=today)
    elif added == 'yesterday':
        qs = qs.filter(date_added=today - timedelta(days=1))
    elif added == 'week':
        qs = qs.filter(date_added__gte=today - timedelta(days=6), date_added__lte=today)
    elif added == 'date':
        if added_from:
            try:
                qs = qs.filter(date_added__gte=datetime.strptime(added_from, '%Y-%m-%d').date())
            except ValueError:
                pass
        if added_to:
            try:
                qs = qs.filter(date_added__lte=datetime.strptime(added_to, '%Y-%m-%d').date())
            except ValueError:
                pass
    return qs


def normalize_candidate_header(value):
    return ''.join(ch for ch in str(value or '').strip().lower() if ch.isalnum())


CANDIDATE_IMPORT_ALIASES = {
    'interview_date': {'interviewdate', 'interviewdatetime', 'date', 'scheduleddate'},
    'full_name': {'candidatename', 'candidate', 'name', 'fullname'},
    'applying_position': {'position', 'appliedfor', 'applyingposition', 'role', 'post'},
    'mobile': {'contactno', 'contactnumber', 'mobileno', 'mobile', 'phone', 'phonenumber'},
    'experience': {
        'yearofexperience',
        'yearofexpereince',
        'yearofexprience',
        'yearofexperiance',
        'yearsofexperience',
        'yearsofexpereince',
        'yearsofexprience',
        'workexperience',
        'totalexperience',
        'totalexp',
        'experience',
        'exp',
    },
    'email': {'mailid', 'email', 'emailid', 'mail'},
    'current_salary': {'currentctc', 'currentc2c', 'currentsalary', 'currentpackage'},
    'expected_salary': {'expectctc', 'expectedctc', 'expectedsalary', 'expectedpackage'},
    'notice_period': {'noticeperiod', 'notice'},
    'location': {'location', 'city', 'place'},
    'status': {'interviewstatus', 'status', 'candidatestatus'},
    'remarks': {'remark', 'remarks', 'note', 'notes', 'comment', 'comments'},
    'source': {'source', 'sources', 'leadsource', 'candidatesource'},
}


def candidate_import_field_for_header(header):
    normalized = normalize_candidate_header(header)
    for field, aliases in CANDIDATE_IMPORT_ALIASES.items():
        if normalized in aliases:
            return field
    if 'interview' in normalized and 'date' in normalized:
        return 'interview_date'
    if normalized.startswith(('year', 'years', 'yr', 'yrs')) and 'exp' in normalized:
        return 'experience'
    if 'experience' in normalized or 'expereince' in normalized or 'experenice' in normalized or 'experince' in normalized:
        return 'experience'
    return ''


def add_candidate_standard_column_fallbacks(field_by_index):
    fields = set(field_by_index.values())
    inverse = {field: index for index, field in field_by_index.items()}
    if 'interview_date' not in fields and 'full_name' in inverse:
        date_index = inverse['full_name'] - 1
        if date_index >= 0 and date_index not in field_by_index:
            field_by_index[date_index] = 'interview_date'
    if 'experience' not in fields and 'mobile' in inverse:
        experience_index = inverse['mobile'] + 1
        if experience_index not in field_by_index:
            field_by_index[experience_index] = 'experience'
    return field_by_index


def candidate_import_rows(uploaded_file):
    filename = uploaded_file.name.lower()
    if filename.endswith('.csv'):
        decoded = uploaded_file.read().decode('utf-8-sig')
        return list(csv.reader(io.StringIO(decoded)))
    if filename.endswith('.xlsx'):
        import openpyxl
        workbook = openpyxl.load_workbook(uploaded_file, read_only=True, data_only=True)
        sheet = workbook.active
        return [list(row) for row in sheet.iter_rows(values_only=True)]
    raise ValidationError('Only .xlsx and .csv candidate import files are allowed.')


def parse_candidate_import_date(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return (datetime(1899, 12, 30) + timedelta(days=int(value))).date()
        except (OverflowError, ValueError):
            return None
    if hasattr(value, 'date'):
        return value.date()
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value
    text = str(value).strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(\d{1,2})(st|nd|rd|th)', r'\1', text, flags=re.IGNORECASE)
    if re.fullmatch(r'\d+(\.0+)?', text):
        serial = int(float(text))
        if 20000 <= serial <= 80000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
    if ' ' in text:
        leading_date = text.split(' ', 1)[0]
        parsed = parse_candidate_import_date(leading_date)
        if parsed:
            return parsed
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        pass
    for fmt in (
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y-%m-%d',
        '%d %b %Y',
        '%d %B %Y',
        '%d-%b-%Y',
        '%d-%B-%Y',
        '%d.%m.%Y',
        '%m/%d/%Y',
        '%d-%m-%y',
        '%d/%m/%y',
        '%d-%b-%y',
        '%d %b %y',
        '%Y/%m/%d',
        '%Y.%m.%d',
        '%b %d, %Y',
        '%B %d, %Y',
        '%b %d %Y',
        '%B %d %Y',
        '%b %d, %y',
        '%B %d, %y',
        '%b %d %y',
        '%B %d %y',
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    for fmt in (
        '%d %b',
        '%d %B',
        '%d-%b',
        '%d-%B',
        '%b %d',
        '%B %d',
    ):
        try:
            parsed_without_year = datetime.strptime(text, fmt).date()
            return parsed_without_year.replace(year=timezone.localdate().year)
        except ValueError:
            continue
    date_patterns = (
        r'\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}',
        r'\d{4}[-/.]\d{1,2}[-/.]\d{1,2}',
        r'\d{1,2}[- ]+[A-Za-z]{3,9}[, -]+\d{2,4}',
        r'[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}',
        r'\d{1,2}[- ]+[A-Za-z]{3,9}',
        r'[A-Za-z]{3,9}\s+\d{1,2}',
    )
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match and match.group(0) != text:
            parsed = parse_candidate_import_date(match.group(0).strip(' ,'))
            if parsed:
                return parsed
    return None


def candidate_status_from_import(value):
    normalized = normalize_candidate_header(value)
    if not normalized:
        return 'new'
    status_aliases = {
        'new': 'new',
        'newcandidate': 'new',
        'applied': 'new',
        'called': 'follow_up_pending',
        'noresponse': 'follow_up_pending',
        'notconnected': 'follow_up_pending',
        'notconnect': 'follow_up_pending',
        'followuppending': 'follow_up_pending',
        'pendingfollowup': 'follow_up_pending',
        'pending': 'follow_up_pending',
        'interviewscheduled': 'interview_scheduled',
        'scheduled': 'interview_scheduled',
        'interviewcompleted': 'interview_scheduled',
        'completed': 'interview_scheduled',
        'selected': 'selected',
        'rejected': 'rejected',
        'joined': 'joined',
        'onhold': 'on_hold',
        'hold': 'on_hold',
    }
    return status_aliases.get(normalized, 'new')


def candidate_source_from_import(value):
    return candidate_text(value)


def candidate_text(value):
    if value is None:
        return ''
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


@login_required
@hr_required
def dashboard(request):
    candidates = candidate_queryset(request)
    today = timezone.localdate()
    recent_candidates = candidates[:5]
    selected_candidate = candidates.first()
    status_counts = OrderedDict((key, candidates.filter(status=key).count()) for key, _ in CANDIDATE_DASHBOARD_STATUS_CHOICES)
    hr_users = User.objects.filter(role='hr').order_by('username')
    hr_performance = [
        {
            'name': user.get_full_name() or user.username,
            'calls': hr_scope(CandidateActivity.objects.filter(candidate__assigned_hr=user, activity_type='call'), request).count(),
            'selected': hr_scope(Candidate.objects.filter(assigned_hr=user, status__in=['selected', 'joined']), request).count(),
            'handled': hr_scope(Candidate.objects.filter(assigned_hr=user), request).count(),
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
        'todays_followups': hr_scope(FollowUp.objects.filter(candidate__in=candidates, completed=False, follow_up_date=today), request).count(),
        'pending_followups': hr_scope(FollowUp.objects.filter(candidate__in=candidates, completed=False), request).count(),
        'status_choices': CANDIDATE_DASHBOARD_STATUS_CHOICES,
        'today_interviews_count': hr_scope(Interview.objects.filter(candidate__in=candidates, date=today), request).count(),
        'today_calls_pending': hr_scope(FollowUp.objects.filter(candidate__in=candidates, completed=False, follow_up_date=today, follow_up_type='call'), request).count(),
        'today_offer_discussions': hr_scope(FollowUp.objects.filter(candidate__in=candidates, completed=False, follow_up_date=today, follow_up_type='meeting'), request).count(),
    }
    return render(request, 'hr/dashboard.html', context)


@login_required
@hr_required
def candidate_list(request):
    qs = candidate_queryset(request)
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    source_labels = dict(Candidate.SOURCE_CHOICES)
    source_values = (
        hr_scope(Candidate.objects.exclude(source=''), request)
        .values_list('source', flat=True)
        .distinct()
        .order_by('source')
    )
    return render(request, 'hr/candidate_list.html', {
        'page_obj': page_obj,
        'status_choices': CANDIDATE_DASHBOARD_STATUS_CHOICES,
        'source_choices': [(source, source_labels.get(source, source)) for source in source_values],
        'query': request.GET.get('q', ''),
        'selected_status': request.GET.get('status', ''),
        'selected_source': request.GET.get('source', ''),
        'selected_added': request.GET.get('added', ''),
        'selected_added_from': request.GET.get('added_from', ''),
        'selected_added_to': request.GET.get('added_to', ''),
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
def candidate_import(request):
    form = CandidateImportForm(request.POST or None, request.FILES or None)
    preview_errors = []
    if request.method == 'POST' and form.is_valid():
        import_date = form.cleaned_data.get('date_added') or timezone.localdate()
        try:
            rows = candidate_import_rows(form.cleaned_data['candidates_file'])
        except (ValidationError, UnicodeDecodeError, ValueError) as exc:
            messages.error(request, f'Unable to read candidate import file: {exc}')
            return render(request, 'hr/candidate_import.html', {'form': form, 'preview_errors': preview_errors})

        header_index = None
        field_by_index = {}
        for index, row in enumerate(rows):
            mapped = {
                col_index: candidate_import_field_for_header(value)
                for col_index, value in enumerate(row)
            }
            mapped = {col_index: field for col_index, field in mapped.items() if field}
            if {'full_name', 'mobile'}.issubset(set(mapped.values())):
                header_index = index
                field_by_index = add_candidate_standard_column_fallbacks(mapped)
                break

        if header_index is None:
            messages.error(request, 'Import failed. Header row must include Candidate Name and Contact No.')
            return render(request, 'hr/candidate_import.html', {'form': form, 'preview_errors': preview_errors})

        created_count = 0
        updated_count = 0
        skipped_count = 0
        scoped_candidates = hr_scope(Candidate.objects.all(), request)

        for row_number, row in enumerate(rows[header_index + 1:], start=header_index + 2):
            data = {}
            for col_index, field in field_by_index.items():
                if col_index < len(row):
                    value = row[col_index]
                    if candidate_text(value) or field not in data:
                        data[field] = value

            full_name = candidate_text(data.get('full_name'))
            mobile = candidate_text(data.get('mobile'))
            if not full_name and not mobile:
                continue
            if not full_name or not mobile:
                skipped_count += 1
                preview_errors.append(f'Row {row_number}: Candidate Name and Contact No are required.')
                continue

            candidate = scoped_candidates.filter(mobile=mobile).first()
            is_new = candidate is None
            if is_new:
                candidate = Candidate(created_by=request.user)

            candidate.full_name = full_name
            candidate.mobile = mobile
            candidate.email = candidate_text(data.get('email'))
            candidate.applying_position = candidate_text(data.get('applying_position')) or candidate.applying_position or 'Not specified'
            imported_experience = candidate_text(data.get('experience'))
            if imported_experience or is_new:
                candidate.experience = imported_experience
            candidate.current_salary = candidate_text(data.get('current_salary'))
            candidate.expected_salary = candidate_text(data.get('expected_salary'))
            candidate.notice_period = candidate_text(data.get('notice_period'))
            candidate.location = candidate_text(data.get('location'))
            imported_interview_date = parse_candidate_import_date(data.get('interview_date'))
            if imported_interview_date or is_new:
                candidate.interview_date = imported_interview_date
            candidate.status = candidate_status_from_import(data.get('status'))
            candidate.source = candidate_source_from_import(data.get('source'))
            candidate.remarks = candidate_text(data.get('remarks'))
            candidate.date_added = import_date
            if not candidate.assigned_hr:
                candidate.assigned_hr = request.user

            candidate.save()
            add_activity(
                candidate,
                'created' if is_new else 'document',
                'Candidate Imported' if is_new else 'Candidate Import Updated',
                request,
                f'Candidate data imported from file row {row_number}.',
            )
            if candidate.remarks:
                CandidateActivity.objects.create(
                    candidate=candidate,
                    activity_type='note',
                    title='Import Remark',
                    description=candidate.remarks[:500],
                    created_by=request.user,
                )

            if is_new:
                created_count += 1
            else:
                updated_count += 1

        if created_count or updated_count:
            messages.success(
                request,
                f'Candidate import completed. Created: {created_count}, Updated: {updated_count}, Skipped: {skipped_count}.',
            )
            return redirect('hr:candidate_list')
        messages.warning(request, f'No candidate records imported. Skipped: {skipped_count}.')

    return render(request, 'hr/candidate_import.html', {'form': form, 'preview_errors': preview_errors})


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
    document_form = CandidateDocumentsForm(instance=candidate)
    tab = request.GET.get('tab', 'overview')
    return render(request, 'hr/candidate_detail.html', {
        'candidate': candidate,
        'note_form': note_form,
        'status_form': status_form,
        'document_form': document_form,
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
def candidate_document_update(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.all(), request), id=candidate_id)
    if request.method == 'POST':
        form = CandidateDocumentsForm(request.POST, request.FILES, instance=candidate)
        if form.is_valid():
            form.save()
            add_activity(candidate, 'update', 'Documents updated', request)
            messages.success(request, 'Documents updated successfully.')
        else:
            messages.error(request, 'Failed to update documents. Please check your files.')
    return redirect(reverse('hr:candidate_detail', args=[candidate.id]) + '?tab=documents')


@login_required
@hr_required
def candidate_download_pdf(request, candidate_id):
    candidate = get_object_or_404(hr_scope(Candidate.objects.select_related('assigned_hr'), request), id=candidate_id)
    
    def get_image_base64(file_field, max_size=(800, 800), quality=70):
        if not file_field:
            return None
        try:
            if not file_field.name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                return None
                
            img = Image.open(file_field.path)
            
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
                
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            buffer = BytesIO()
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{img_str}"
        except Exception:
            return None
            
    context = {
        'candidate': candidate, 
        'request': request,
        'resume_b64': get_image_base64(candidate.resume),
        'photo_b64': get_image_base64(candidate.photo, max_size=(300, 300)),

    }
    
    template = get_template('hr/candidate_pdf.html')
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="candidate_{candidate.id}_{candidate.full_name}.pdf"'
    
    if pisa:
        pisa_status = pisa.CreatePDF(html, dest=response)
        if pisa_status.err:
            return HttpResponse('We had some errors generating the PDF.')
    else:
        return HttpResponse('PDF generation library not installed.')
        
    return response


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
    base = hr_scope(FollowUp.objects.select_related('candidate', 'handled_by'), request).filter(candidate__in=candidates)
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
    interviews = hr_scope(Interview.objects.select_related('candidate', 'scheduled_by'), request).filter(candidate__in=candidates)
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
        'interview_count': hr_scope(Interview.objects.filter(candidate__in=candidates), request).count(),
        'followup_count': hr_scope(FollowUp.objects.filter(candidate__in=candidates), request).count(),
        'selection_ratio': round((candidates.filter(status__in=['selected', 'joined']).count() / total) * 100, 1),
    })


@login_required
@hr_required
def performance(request):
    users = User.objects.filter(role='hr').order_by('username')
    rows = []
    for user in users:
        handled = hr_scope(Candidate.objects.filter(assigned_hr=user), request).count()
        selected = hr_scope(Candidate.objects.filter(assigned_hr=user, status__in=['selected', 'joined']), request).count()
        rejected = hr_scope(Candidate.objects.filter(assigned_hr=user, status='rejected'), request).count()
        calls = hr_scope(CandidateActivity.objects.filter(candidate__assigned_hr=user, activity_type='call'), request).count()
        interviews = hr_scope(Interview.objects.filter(candidate__assigned_hr=user), request).count()
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
    writer.writerow([
        'Interview Date',
        'Candidate Name',
        'Position',
        'Contact No',
        'Year of Experience',
        'Mail Id',
        'Current CTC',
        'Expected CTC',
        'Notice Period',
        'Location',
        'Interview Status',
        'Remark',
        'Source',
        'Assigned HR',
    ])
    for candidate in candidate_queryset(request):
        writer.writerow([
            candidate.interview_date,
            candidate.full_name,
            candidate.applying_position,
            candidate.mobile,
            candidate.experience,
            candidate.email,
            candidate.current_salary,
            candidate.expected_salary,
            candidate.notice_period,
            candidate.location,
            candidate.get_status_display(),
            candidate.remarks,
            candidate.source_display,
            candidate.assigned_hr.username if candidate.assigned_hr else '',
        ])
    return response


def placement_metrics(request):
    total_sent = hr_scope(PlacementStudentAssignment.objects.all(), request).count()
    selected = hr_scope(PlacementStudentAssignment.objects.filter(final_status='selected'), request).count()
    rejected = hr_scope(PlacementStudentAssignment.objects.filter(final_status='rejected'), request).count()
    placed = hr_scope(PlacementStudentAssignment.objects.filter(final_status='joined'), request).count()
    rate = round((placed / total_sent) * 100, 2) if total_sent else 0
    return [
        {'label': 'Total Companies', 'icon': 'bi-buildings-fill', 'color': 'violet', 'value': hr_scope(PlacementCompany.objects.all(), request).count(), 'trend': '+8 this month', 'spark': [22, 55, 70]},
        {'label': 'Total Drives', 'icon': 'bi-megaphone-fill', 'color': 'emerald', 'value': hr_scope(PlacementDrive.objects.all(), request).count(), 'trend': '+3 this month', 'spark': [30, 45, 68]},
        {'label': 'Employees Eligible', 'icon': 'bi-mortarboard-fill', 'color': 'blue', 'value': StudentProfile.objects.count(), 'trend': '+24 this month', 'spark': [18, 55, 86]},
        {'label': 'Employees Sent', 'icon': 'bi-send-fill', 'color': 'orange', 'value': total_sent, 'trend': '+15 this month', 'spark': [28, 62, 73]},
        {'label': 'Employees Selected', 'icon': 'bi-person-check-fill', 'color': 'teal', 'value': selected, 'trend': '+10 this month', 'spark': [18, 42, 64]},
        {'label': 'Employees Rejected', 'icon': 'bi-person-x-fill', 'color': 'red', 'value': rejected, 'trend': '+4 this month', 'spark': [12, 35, 40]},
        {'label': 'Employees Placed', 'icon': 'bi-award-fill', 'color': 'indigo', 'value': placed, 'trend': '+5 this month', 'spark': [12, 44, 66]},
        {'label': 'Placement Rate', 'icon': 'bi-graph-up-arrow', 'color': 'amber', 'value': f'{rate}%', 'trend': '+3.45% this month', 'spark': [20, 58, 78]},
    ]


@login_required
@hr_required
def placement_dashboard(request):
    drives = hr_scope(PlacementDrive.objects.select_related('company'), request)[:6]
    status_counts = OrderedDict((key, hr_scope(PlacementDrive.objects.filter(status=key), request).count()) for key, _ in PlacementDrive.STATUS_CHOICES)
    total_drives = max(sum(status_counts.values()), 1)
    top_companies = sorted(hr_scope(PlacementCompany.objects.all(), request), key=lambda company: company.joined_count, reverse=True)[:5]
    context = {
        'metrics': placement_metrics(request),
        'recent_drives': drives,
        'top_companies': top_companies,
        'status_counts': status_counts,
        'total_drives': total_drives,
        'activities': hr_scope(PlacementActivity.objects.select_related('company', 'drive', 'created_by'), request)[:6],
        'upcoming_interviews': hr_scope(PlacementInterview.objects.select_related('company', 'drive', 'assignment'), request)[:5],
        'pipeline': {
            'scheduled': hr_scope(PlacementDrive.objects.exclude(status='cancelled'), request).count(),
            'shortlisted': hr_scope(PlacementStudentAssignment.objects.all(), request).count(),
            'appeared': hr_scope(PlacementStudentAssignment.objects.filter(interview_status__in=['appeared', 'selected', 'rejected', 'joined']), request).count(),
            'offers': hr_scope(PlacementOffer.objects.exclude(offer_status='pending'), request).count(),
            'placed': hr_scope(PlacementStudentAssignment.objects.filter(final_status='joined'), request).count(),
        },
    }
    return render(request, 'hr/placement_dashboard.html', context)


@login_required
@hr_required
def placement_company_list(request):
    companies = hr_scope(PlacementCompany.objects.all(), request)
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
    company = get_object_or_404(hr_scope(PlacementCompany.objects.all(), request), id=company_id)
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
    company = get_object_or_404(hr_scope(PlacementCompany.objects.all(), request), id=company_id)
    assignments = company.placement_assignments.select_related('student', 'drive')[:20]
    return render(request, 'hr/placement_company_detail.html', {'company': company, 'assignments': assignments})


@login_required
@hr_required
def placement_company_delete(request, company_id):
    company = get_object_or_404(hr_scope(PlacementCompany.objects.all(), request), id=company_id)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Company deleted successfully.')
        return redirect('hr:placement_company_list')
    return render(request, 'hr/confirm_delete.html', {'object': company, 'cancel_url': reverse('hr:placement_company_detail', args=[company.id])})


@login_required
@hr_required
def placement_drive_list(request):
    drives = hr_scope(PlacementDrive.objects.select_related('company'), request)
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
    company = get_object_or_404(hr_scope(PlacementCompany.objects.all(), request), id=company_id) if company_id else None
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
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.all(), request), id=drive_id)
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
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.select_related('company'), request), id=drive_id)
    assignments = drive.assignments.select_related('student', 'company')[:30]
    return render(request, 'hr/placement_drive_detail.html', {'drive': drive, 'assignments': assignments})


@login_required
@hr_required
def placement_assign_students(request, drive_id):
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.select_related('company'), request), id=drive_id)
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
            add_placement_activity('assignment', f'{created} employees assigned to {drive.company or drive}', request, drive=drive, company=drive.company)
        messages.success(request, f'{created} employees assigned successfully.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_assign_students.html', {'drive': drive, 'students': students[:100], 'query': query})


@login_required
@hr_required
def placement_student_list(request):
    assignments = hr_scope(PlacementStudentAssignment.objects.select_related('student', 'company', 'drive'), request)
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    if status:
        assignments = assignments.filter(Q(interview_status=status) | Q(final_status=status))
    if query:
        assignments = assignments.filter(
            Q(student_name__icontains=query)
            | Q(student__full_name__icontains=query)
            | Q(student__user__username__icontains=query)
            | Q(company__name__icontains=query)
        )
    page_obj = Paginator(assignments, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_student_list.html', {
        'page_obj': page_obj,
        'status_choices': PlacementStudentAssignment.ASSIGNMENT_STATUS_CHOICES,
        'status': status,
        'query': query,
    })


@login_required
@hr_required
def placement_assignment_create(request, drive_id=None, company_id=None):
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.all(), request), id=drive_id) if drive_id else None
    company = get_object_or_404(hr_scope(PlacementCompany.objects.all(), request), id=company_id) if company_id else None
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
        messages.success(request, 'Employee assignment saved successfully.')
        if company_id:
            return redirect('hr:placement_company_detail', company_id=company_id)
        elif drive_id:
            return redirect('hr:placement_drive_detail', drive_id=drive_id)
        return redirect('hr:placement_employee_list')
    return render(request, 'hr/placement_assignment_form.html', {'form': form, 'drive': drive, 'company': company})


@login_required
@hr_required
def placement_assignment_edit(request, assignment_id):
    assignment = get_object_or_404(hr_scope(PlacementStudentAssignment.objects.all(), request), id=assignment_id)
    form = PlacementAssignmentForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save()
        messages.success(request, 'Employee placement updated successfully.')
        return redirect('hr:placement_employee_list')
    return render(request, 'hr/placement_assignment_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def placement_interview_list(request):
    interviews = hr_scope(PlacementInterview.objects.select_related('company', 'drive', 'assignment'), request)
    page_obj = Paginator(interviews, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_interview_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def placement_interview_create(request, drive_id=None, assignment_id=None):
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.all(), request), id=drive_id) if drive_id else None
    assignment = get_object_or_404(hr_scope(PlacementStudentAssignment.objects.all(), request), id=assignment_id) if assignment_id else None
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
            interview.assignment.sync_final_status_from_interview_status()
            interview.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        add_placement_activity('interview', f'Interview scheduled for {interview.assignment or interview.company or "employee"}', request, company=interview.company, drive=interview.drive)
        messages.success(request, 'Placement interview saved successfully.')
        return redirect('hr:placement_interview_list')
    return render(request, 'hr/placement_interview_form.html', {'form': form, 'drive': drive, 'assignment': assignment})


@login_required
@hr_required
def placement_interview_edit(request, interview_id):
    interview = get_object_or_404(hr_scope(PlacementInterview.objects.all(), request), id=interview_id)
    form = PlacementInterviewForm(request.POST or None, instance=interview)
    if request.method == 'POST' and form.is_valid():
        interview = form.save()
        if interview.assignment:
            interview.assignment.interview_status = interview.status
            if interview.status == 'selected':
                interview.assignment.final_status = 'selected'
            elif interview.status == 'rejected':
                interview.assignment.final_status = 'rejected'
            interview.assignment.sync_final_status_from_interview_status()
            interview.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        messages.success(request, 'Placement interview updated successfully.')
        return redirect('hr:placement_interview_list')
    return render(request, 'hr/placement_interview_form.html', {'form': form, 'interview': interview})


@login_required
@hr_required
def placement_offer_list(request):
    offers = hr_scope(PlacementOffer.objects.select_related('assignment', 'assignment__student', 'company'), request)
    page_obj = Paginator(offers, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/placement_offer_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def placement_offer_create(request, assignment_id=None):
    assignment = get_object_or_404(hr_scope(PlacementStudentAssignment.objects.all(), request), id=assignment_id) if assignment_id else None
    instance = hr_scope(PlacementOffer.objects.filter(assignment=assignment), request).first() if assignment else None
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
                offer.assignment.interview_status = 'joined'
            elif offer.offer_status in ('offered', 'accepted'):
                offer.assignment.final_status = 'selected'
                offer.assignment.interview_status = 'selected'
            elif offer.offer_status == 'rejected':
                offer.assignment.final_status = 'rejected'
                offer.assignment.interview_status = 'rejected'
            offer.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        add_placement_activity('offer', f'Offer updated for {offer.assignment or offer.company}', request, company=offer.company)
        messages.success(request, 'Offer and placement saved successfully.')
        return redirect('hr:placement_offer_list')
    return render(request, 'hr/placement_offer_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def placement_offer_edit(request, offer_id):
    offer = get_object_or_404(hr_scope(PlacementOffer.objects.all(), request), id=offer_id)
    form = PlacementOfferForm(request.POST or None, instance=offer)
    if request.method == 'POST' and form.is_valid():
        offer = form.save()
        if offer.assignment:
            if offer.joining_status == 'joined':
                offer.assignment.final_status = 'joined'
                offer.assignment.interview_status = 'joined'
            elif offer.offer_status in ('offered', 'accepted'):
                offer.assignment.final_status = 'selected'
                offer.assignment.interview_status = 'selected'
            elif offer.offer_status == 'rejected':
                offer.assignment.final_status = 'rejected'
                offer.assignment.interview_status = 'rejected'
            offer.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        messages.success(request, 'Offer updated successfully.')
        return redirect('hr:placement_offer_list')
    return render(request, 'hr/placement_offer_form.html', {'form': form, 'offer': offer})


@login_required
@hr_required
def placement_reports(request):
    companies = hr_scope(PlacementCompany.objects.all(), request)
    assignments = hr_scope(PlacementStudentAssignment.objects.select_related('company', 'drive', 'student'), request)
    company_id = request.GET.get('company', '').strip()
    status = request.GET.get('status', '').strip()
    if company_id:
        assignments = assignments.filter(company_id=company_id)
    if status:
        assignments = assignments.filter(Q(interview_status=status) | Q(final_status=status))
    return render(request, 'hr/placement_reports.html', {
        'companies': companies,
        'assignments': assignments[:100],
        'company_id': company_id,
        'status': status,
        'status_choices': PlacementStudentAssignment.ASSIGNMENT_STATUS_CHOICES,
        'summary': {
            'companies': companies.count(),
            'drives': hr_scope(PlacementDrive.objects.all(), request).count(),
            'sent': hr_scope(PlacementStudentAssignment.objects.all(), request).count(),
            'selected': hr_scope(PlacementStudentAssignment.objects.filter(Q(interview_status='selected') | Q(final_status='selected')), request).count(),
            'rejected': hr_scope(PlacementStudentAssignment.objects.filter(Q(interview_status='rejected') | Q(final_status='rejected')), request).count(),
            'joined': hr_scope(PlacementStudentAssignment.objects.filter(Q(interview_status='joined') | Q(final_status='joined')), request).count(),
        },
    })


@login_required
@hr_required
def export_placement_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="placement-report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Employee', 'Designation', 'Company', 'Drive', 'Status'])
    for item in hr_scope(PlacementStudentAssignment.objects.select_related('student', 'company', 'drive'), request):
        writer.writerow([
            item.display_name,
            item.display_course,
            item.company.name if item.company else '',
            item.drive.job_role if item.drive else '',
            item.assignment_status_display,
        ])
    return response


# ──────────────────────────────── PLACEMENT ASSIGNMENT DETAIL ────────────────────────────────

@login_required
@hr_required
def placement_assignment_detail(request, assignment_id):
    assignment = get_object_or_404(hr_scope(PlacementStudentAssignment.objects.all(), request), id=assignment_id)
    return render(request, 'hr/placement_assignment_detail.html', {'assignment': assignment})


# ──────────────────────────────── PROJECT VIEWS ────────────────────────────────

def add_project_activity(activity_type, title, request=None, description='', company=None, drive=None):
    ProjectActivity.objects.create(
        activity_type=activity_type,
        title=title,
        description=description,
        company=company,
        drive=drive,
        created_by=request.user if request and request.user.is_authenticated else None,
    )


@login_required
@hr_required
def project_dashboard(request):
    companies = hr_scope(ProjectCompany.objects.all(), request)
    drives = hr_scope(ProjectDrive.objects.select_related('company'), request)[:6]
    assignments = hr_scope(ProjectEmployeeAssignment.objects.select_related('employee', 'company', 'drive'), request)
    assignment_status_counts = {
        'selected': assignments.filter(Q(interview_status='selected') | Q(final_status='selected')).count(),
        'rejected': assignments.filter(Q(interview_status='rejected') | Q(final_status='rejected')).count(),
        'allocated': assignments.filter(Q(interview_status='allocated') | Q(final_status='allocated')).count(),
        'released': assignments.filter(Q(interview_status='released') | Q(final_status='released')).count(),
        'pending': assignments.filter(Q(interview_status='pending') | Q(final_status='pending')).count(),
    }
    status_counts = {key: hr_scope(ProjectDrive.objects.filter(status=key), request).count() for key, _ in ProjectDrive.STATUS_CHOICES}
    total_drives = max(sum(status_counts.values()), 1)
    top_companies = sorted(companies, key=lambda c: c.allocated_count, reverse=True)[:5]
    employee_list_url = reverse('hr:project_employee_list')
    context = {
        'recent_drives': drives,
        'top_companies': top_companies,
        'status_counts': status_counts,
        'total_drives': total_drives,
        'activities': hr_scope(ProjectActivity.objects.all(), request)[:6],
        'upcoming_interviews': hr_scope(ProjectInterview.objects.select_related('company', 'drive', 'assignment'), request)[:5],
        'metrics': [
            {'label': 'Total Companies', 'icon': 'bi-buildings-fill', 'color': 'violet', 'value': companies.count(), 'url': reverse('hr:project_company_list')},
            {'label': 'Total Drives', 'icon': 'bi-megaphone-fill', 'color': 'emerald', 'value': hr_scope(ProjectDrive.objects.all(), request).count(), 'url': reverse('hr:project_drive_list')},
            {'label': 'Employees Assigned', 'icon': 'bi-people-fill', 'color': 'blue', 'value': assignments.count(), 'url': employee_list_url},
            {'label': 'Employees Selected', 'icon': 'bi-person-check', 'color': 'green', 'value': assignment_status_counts.get('selected', 0), 'url': f'{employee_list_url}?status=selected'},
            {'label': 'Employees Rejected', 'icon': 'bi-person-x', 'color': 'crimson', 'value': assignment_status_counts.get('rejected', 0), 'url': f'{employee_list_url}?status=rejected'},
            {'label': 'Employees Allocated', 'icon': 'bi-person-check-fill', 'color': 'teal', 'value': assignment_status_counts.get('allocated', 0), 'url': f'{employee_list_url}?status=allocated'},
            {'label': 'Employees Released', 'icon': 'bi-person-x-fill', 'color': 'red', 'value': assignment_status_counts.get('released', 0), 'url': f'{employee_list_url}?status=released'},
            {'label': 'Pending', 'icon': 'bi-hourglass-split', 'color': 'amber', 'value': assignment_status_counts.get('pending', 0), 'url': f'{employee_list_url}?status=pending'},
        ],
        'pipeline': {
            'scheduled': hr_scope(ProjectDrive.objects.exclude(status='cancelled'), request).count(),
            'sent': hr_scope(ProjectEmployeeAssignment.objects.all(), request).count(),
            'appeared': hr_scope(ProjectEmployeeAssignment.objects.filter(interview_status__in=['appeared', 'selected', 'rejected', 'allocated', 'released']), request).count(),
            'allocations': hr_scope(ProjectAllocation.objects.all(), request).count(),
            'allocated': hr_scope(ProjectEmployeeAssignment.objects.filter(Q(interview_status='allocated') | Q(final_status='allocated')), request).count(),
        },
    }
    return render(request, 'hr/project_dashboard.html', context)


@login_required
@hr_required
def project_company_list(request):
    companies = hr_scope(ProjectCompany.objects.all(), request)
    query = request.GET.get('q', '').strip()
    if query:
        companies = companies.filter(
            Q(name__icontains=query) | Q(industry__icontains=query) | Q(contact_person__icontains=query) | Q(city__icontains=query)
        )
    page_obj = Paginator(companies, 12).get_page(request.GET.get('page'))
    return render(request, 'hr/project_company_list.html', {'page_obj': page_obj, 'query': query})


@login_required
@hr_required
def project_company_create(request):
    form = ProjectCompanyForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        company = form.save(commit=False)
        company.created_by = request.user
        company.save()
        add_project_activity('company', f'{company} added', request, 'Company profile saved.', company=company)
        messages.success(request, 'Company saved successfully.')
        return redirect('hr:project_company_detail', company_id=company.id)
    return render(request, 'hr/project_company_form.html', {'form': form, 'title': 'Add Company'})


@login_required
@hr_required
def project_company_edit(request, company_id):
    company = get_object_or_404(hr_scope(ProjectCompany.objects.all(), request), id=company_id)
    form = ProjectCompanyForm(request.POST or None, request.FILES or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        company = form.save()
        add_project_activity('company', f'{company} updated', request, 'Company profile updated.', company=company)
        messages.success(request, 'Company updated successfully.')
        return redirect('hr:project_company_detail', company_id=company.id)
    return render(request, 'hr/project_company_form.html', {'form': form, 'title': 'Edit Company', 'company': company})


@login_required
@hr_required
def project_company_detail(request, company_id):
    company = get_object_or_404(hr_scope(ProjectCompany.objects.all(), request), id=company_id)
    drives = company.drives.all()
    assignments = company.project_assignments.select_related('employee', 'drive').all()
    activities = company.activities.all()[:10]
    return render(request, 'hr/project_company_detail.html', {
        'company': company,
        'drives': drives,
        'assignments': assignments,
        'activities': activities,
    })


@login_required
@hr_required
def project_drive_list(request):
    drives = hr_scope(ProjectDrive.objects.select_related('company'), request)
    status = request.GET.get('status', '').strip()
    if status:
        drives = drives.filter(status=status)
    page_obj = Paginator(drives, 12).get_page(request.GET.get('page'))
    return render(request, 'hr/project_drive_list.html', {
        'page_obj': page_obj,
        'status': status,
        'status_choices': ProjectDrive.STATUS_CHOICES,
    })


@login_required
@hr_required
def project_drive_create(request, company_id=None):
    company = get_object_or_404(hr_scope(ProjectCompany.objects.all(), request), id=company_id) if company_id else None
    form = ProjectDriveForm(request.POST or None, company=company)
    if request.method == 'POST' and form.is_valid():
        drive = form.save(commit=False)
        if company:
            drive.company = company
        drive.created_by = request.user
        drive.save()
        add_project_activity('drive', f'Project drive created for {drive.company or "company"}', request, company=drive.company, drive=drive)
        messages.success(request, 'Project drive saved successfully.')
        return redirect('hr:project_drive_detail', drive_id=drive.id)
    return render(request, 'hr/project_drive_form.html', {'form': form, 'company': company})


@login_required
@hr_required
def project_drive_edit(request, drive_id):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id)
    form = ProjectDriveForm(request.POST or None, instance=drive)
    if request.method == 'POST' and form.is_valid():
        drive = form.save()
        add_project_activity('drive', f'{drive} updated', request, company=drive.company, drive=drive)
        messages.success(request, 'Project drive updated.')
        return redirect('hr:project_drive_detail', drive_id=drive.id)
    return render(request, 'hr/project_drive_form.html', {'form': form, 'drive': drive})


@login_required
@hr_required
def project_drive_detail(request, drive_id):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id)
    assignments = drive.assignments.select_related('employee').all()
    interviews = drive.project_interviews.all()
    activities = drive.activities.all()[:10]
    return render(request, 'hr/project_drive_detail.html', {
        'drive': drive,
        'assignments': assignments,
        'interviews': interviews,
        'activities': activities,
    })


@login_required
@hr_required
def project_assign_employees(request, drive_id):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id)
    query = request.GET.get('q', '').strip()
    employees = hr_scope(ExternalEmployee.objects.filter(status='active'), request)
    if query:
        employees = employees.filter(Q(full_name__icontains=query) | Q(employee_id__icontains=query) | Q(department__icontains=query))
    if request.method == 'POST':
        employee_ids = request.POST.getlist('employee_ids')
        created = 0
        for eid in employee_ids:
            emp = hr_scope(ExternalEmployee.objects.filter(id=eid), request).first()
            if emp and not hr_scope(ProjectEmployeeAssignment.objects.filter(drive=drive, employee=emp), request).exists():
                ProjectEmployeeAssignment.objects.create(
                    drive=drive,
                    company=drive.company,
                    employee=emp,
                    employee_name=emp.full_name,
                    employee_code=emp.employee_id,
                    department=emp.department,
                    designation=emp.designation,
                    assigned_by=request.user,
                )
                created += 1
        if created:
            add_project_activity('assignment', f'{created} employees assigned to {drive.company or drive}', request, company=drive.company, drive=drive)
        messages.success(request, f'{created} employees assigned successfully.')
        return redirect('hr:project_drive_detail', drive_id=drive.id)
    return render(request, 'hr/project_assign_employees.html', {'drive': drive, 'employees': employees[:100], 'query': query})


@login_required
@hr_required
def project_employee_list(request):
    assignments = hr_scope(ProjectEmployeeAssignment.objects.select_related('employee', 'company', 'drive'), request)
    status = request.GET.get('status', '').strip()
    query = request.GET.get('q', '').strip()
    if status:
        assignments = assignments.filter(Q(interview_status=status) | Q(final_status=status))
    if query:
        assignments = assignments.filter(
            Q(employee_name__icontains=query) | Q(employee__full_name__icontains=query) | Q(company__name__icontains=query)
        )
    page_obj = Paginator(assignments, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/project_employee_list.html', {
        'page_obj': page_obj,
        'status_choices': ProjectEmployeeAssignment.ASSIGNMENT_STATUS_CHOICES,
        'status': status,
        'query': query,
    })


@login_required
@hr_required
def project_assignment_create(request, drive_id=None, company_id=None):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id) if drive_id else None
    company = get_object_or_404(hr_scope(ProjectCompany.objects.all(), request), id=company_id) if company_id else None
    form = ProjectAssignmentForm(request.POST or None, drive=drive, company=company)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save(commit=False)
        if drive:
            assignment.drive = drive
            assignment.company = drive.company
        elif company:
            assignment.company = company
        if assignment.employee:
            assignment.employee_name = assignment.employee_name or assignment.employee.full_name
            assignment.employee_code = assignment.employee_code or assignment.employee.employee_id
            assignment.department = assignment.department or assignment.employee.department
            assignment.designation = assignment.designation or assignment.employee.designation
        assignment.assigned_by = request.user
        assignment.save()
        add_project_activity('assignment', f'{assignment.display_name} assigned to {assignment.company or "company"}', request, company=assignment.company, drive=assignment.drive)
        messages.success(request, 'Employee assignment saved successfully.')
        return redirect('hr:project_employee_list')
    return render(request, 'hr/project_assignment_form.html', {'form': form, 'drive': drive, 'company': company})


@login_required
@hr_required
def project_assignment_edit(request, assignment_id):
    assignment = get_object_or_404(hr_scope(ProjectEmployeeAssignment.objects.all(), request), id=assignment_id)
    form = ProjectAssignmentForm(request.POST or None, instance=assignment)
    if request.method == 'POST' and form.is_valid():
        assignment = form.save()
        messages.success(request, 'Employee assignment updated successfully.')
        return redirect('hr:project_employee_list')
    return render(request, 'hr/project_assignment_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def project_assignment_detail(request, assignment_id):
    assignment = get_object_or_404(hr_scope(ProjectEmployeeAssignment.objects.all(), request), id=assignment_id)
    return render(request, 'hr/project_assignment_detail.html', {'assignment': assignment})


@login_required
@hr_required
def project_interview_list(request):
    interviews = hr_scope(ProjectInterview.objects.select_related('company', 'drive', 'assignment'), request)
    page_obj = Paginator(interviews, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/project_interview_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def project_interview_create(request, drive_id=None, assignment_id=None):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id) if drive_id else None
    assignment = get_object_or_404(hr_scope(ProjectEmployeeAssignment.objects.all(), request), id=assignment_id) if assignment_id else None
    form = ProjectInterviewForm(request.POST or None, drive=drive, assignment=assignment)
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
            interview.assignment.sync_final_status_from_interview_status()
            interview.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        add_project_activity('interview', f'Interview scheduled for {interview.assignment or interview.company}', request, company=interview.company, drive=interview.drive)
        messages.success(request, 'Project interview saved successfully.')
        return redirect('hr:project_interview_list')
    return render(request, 'hr/project_interview_form.html', {'form': form, 'drive': drive, 'assignment': assignment})


@login_required
@hr_required
def project_interview_edit(request, interview_id):
    interview = get_object_or_404(hr_scope(ProjectInterview.objects.all(), request), id=interview_id)
    form = ProjectInterviewForm(request.POST or None, instance=interview)
    if request.method == 'POST' and form.is_valid():
        interview = form.save()
        if interview.assignment:
            interview.assignment.interview_status = interview.status
            if interview.status == 'selected':
                interview.assignment.final_status = 'selected'
            elif interview.status == 'rejected':
                interview.assignment.final_status = 'rejected'
            interview.assignment.sync_final_status_from_interview_status()
            interview.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        messages.success(request, 'Project interview updated.')
        return redirect('hr:project_interview_list')
    return render(request, 'hr/project_interview_form.html', {'form': form, 'interview': interview})


@login_required
@hr_required
def project_allocation_list(request):
    allocations = hr_scope(ProjectAllocation.objects.select_related('assignment', 'assignment__employee', 'company'), request)
    page_obj = Paginator(allocations, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/project_allocation_list.html', {'page_obj': page_obj})


@login_required
@hr_required
def project_allocation_create(request, assignment_id=None):
    assignment = get_object_or_404(hr_scope(ProjectEmployeeAssignment.objects.all(), request), id=assignment_id) if assignment_id else None
    instance = hr_scope(ProjectAllocation.objects.filter(assignment=assignment), request).first() if assignment else None
    form = ProjectAllocationForm(request.POST or None, assignment=assignment, instance=instance)
    if request.method == 'POST' and form.is_valid():
        allocation = form.save(commit=False)
        if assignment:
            allocation.assignment = assignment
            allocation.company = assignment.company
        allocation.created_by = allocation.created_by or request.user
        allocation.save()
        if allocation.assignment:
            if allocation.allocation_status == 'allocated':
                allocation.assignment.final_status = 'allocated'
                allocation.assignment.interview_status = 'allocated'
            elif allocation.allocation_status == 'released':
                allocation.assignment.final_status = 'released'
                allocation.assignment.interview_status = 'released'
            allocation.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        add_project_activity('allocation', f'Allocation updated for {allocation.assignment or allocation.company}', request, company=allocation.company)
        messages.success(request, 'Allocation saved successfully.')
        return redirect('hr:project_allocation_list')
    return render(request, 'hr/project_allocation_form.html', {'form': form, 'assignment': assignment})


@login_required
@hr_required
def project_allocation_edit(request, allocation_id):
    allocation = get_object_or_404(hr_scope(ProjectAllocation.objects.all(), request), id=allocation_id)
    form = ProjectAllocationForm(request.POST or None, instance=allocation)
    if request.method == 'POST' and form.is_valid():
        allocation = form.save()
        if allocation.assignment:
            if allocation.allocation_status == 'allocated':
                allocation.assignment.final_status = 'allocated'
                allocation.assignment.interview_status = 'allocated'
            elif allocation.allocation_status == 'released':
                allocation.assignment.final_status = 'released'
                allocation.assignment.interview_status = 'released'
            allocation.assignment.save(update_fields=['interview_status', 'final_status', 'updated_at'])
        messages.success(request, 'Allocation updated successfully.')
        return redirect('hr:project_allocation_list')
    return render(request, 'hr/project_allocation_form.html', {'form': form, 'allocation': allocation})


@login_required
@hr_required
def project_reports(request):
    companies = hr_scope(ProjectCompany.objects.all(), request)
    assignments = hr_scope(ProjectEmployeeAssignment.objects.select_related('company', 'drive', 'employee'), request)
    company_id = request.GET.get('company', '').strip()
    status = request.GET.get('status', '').strip()
    if company_id:
        assignments = assignments.filter(company_id=company_id)
    if status:
        assignments = assignments.filter(Q(interview_status=status) | Q(final_status=status))
    return render(request, 'hr/project_reports.html', {
        'companies': companies,
        'assignments': assignments[:100],
        'company_id': company_id,
        'status': status,
        'status_choices': ProjectEmployeeAssignment.ASSIGNMENT_STATUS_CHOICES,
        'summary': {
            'companies': companies.count(),
            'drives': hr_scope(ProjectDrive.objects.all(), request).count(),
            'sent': hr_scope(ProjectEmployeeAssignment.objects.all(), request).count(),
            'selected': hr_scope(ProjectEmployeeAssignment.objects.filter(Q(interview_status='selected') | Q(final_status='selected')), request).count(),
            'rejected': hr_scope(ProjectEmployeeAssignment.objects.filter(Q(interview_status='rejected') | Q(final_status='rejected')), request).count(),
            'allocated': hr_scope(ProjectEmployeeAssignment.objects.filter(Q(interview_status='allocated') | Q(final_status='allocated')), request).count(),
            'released': hr_scope(ProjectEmployeeAssignment.objects.filter(Q(interview_status='released') | Q(final_status='released')), request).count(),
        },
    })


@login_required
@hr_required
def export_project_report(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="project-report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Employee', 'Code', 'Department', 'Company', 'Drive', 'Status'])
    for item in hr_scope(ProjectEmployeeAssignment.objects.select_related('employee', 'company', 'drive'), request):
        writer.writerow([
            item.display_name,
            item.employee_code,
            item.department,
            item.company.name if item.company else '',
            item.drive.project_name if item.drive else '',
            item.assignment_status_display,
        ])
    return response


# ──────────────────────────────── EXTERNAL EMPLOYEE VIEWS ────────────────────────────────

@login_required
@hr_required
def external_attendance_dashboard(request, branch_slug='thane'):
    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    today = timezone.localdate()
    
    query = request.GET.get('q', '').strip()
    selected_department = request.GET.get('department', '').strip()
    selected_status = request.GET.get('status', '').strip()
    
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            from datetime import datetime
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = today
    else:
        selected_date = today

    base_employees = hr_scope(ExternalEmployee.objects.filter(branch=branch_slug, status='active'), request)
    
    # KPIs Data
    total_emp = base_employees.count()
    today_logs = hr_scope(ExternalAttendanceLog.objects.filter(employee__branch=branch_slug, date=today), request)
    present_today = today_logs.filter(status='present').count()
    absent_today = today_logs.filter(status='absent').count()
    late_today = today_logs.filter(status='present', late_minutes__gt=0).count()
    
    kpis = [
        {'label': 'Total Employees', 'icon': 'bi-people', 'color': 'blue', 'value': total_emp, 'meta': f'Active in {branch}'},
        {'label': 'Present Today', 'icon': 'bi-check-circle', 'color': 'emerald', 'value': present_today},
        {'label': 'Absent Today', 'icon': 'bi-x-circle', 'color': 'red', 'value': absent_today},
        {'label': 'Late Today', 'icon': 'bi-clock-history', 'color': 'amber', 'value': late_today},
    ]

    employees = base_employees
    if selected_department:
        employees = employees.filter(department=selected_department)
    if query:
        employees = employees.filter(Q(full_name__icontains=query) | Q(employee_id__icontains=query))

    logs = ExternalAttendanceLog.objects.filter(employee__in=employees, date=selected_date)
    log_dict = {log.employee_id: log for log in logs}

    rows = []
    for emp in employees:
        log = log_dict.get(emp.id)
        att_status = log.status if log else ''
        
        if selected_status and att_status != selected_status:
            continue

        # Calculate initials
        names = emp.full_name.strip().split()
        if len(names) >= 2:
            initials = (names[0][0] + names[-1][0]).upper()
        elif len(names) == 1:
            initials = names[0][:2].upper()
        else:
            initials = 'NA'

        rows.append({
            'employee_pk': emp.pk,
            'full_name': emp.full_name,
            'initials': initials,
            'employee_id': emp.employee_id,
            'department': emp.department,
            'attendance_status': att_status,
            'date': log.date if log else selected_date,
            'check_in': log.check_in.strftime('%I:%M %p') if log and log.check_in else '--:--',
            'check_out': log.check_out.strftime('%I:%M %p') if log and log.check_out else '--:--',
            'working_hours': log.working_hours_display if log and log.working_hours else '--',
            'late_minutes': log.late_minutes if log else 0,
            'remarks': log.notes if log else '',
            'is_db': True,
        })
        
    if not rows and not base_employees.exists():
        rows = [{
            'employee_pk': '',
            'full_name': 'Sample Employee',
            'employee_id': 'E-0000',
            'department': 'Sample Department',
            'attendance_status': 'present',
            'remarks': 'Sample data only',
            'is_db': False,
        }]

    departments = base_employees.values_list('department', flat=True).distinct()
    
    page_obj = Paginator(rows, 15).get_page(request.GET.get('page'))

    context = {
        'branch': branch,
        'external_branch_slug': branch_slug,
        'kpis': kpis,
        'page_obj': page_obj,
        'query': query,
        'external_selected_date': selected_date.strftime('%Y-%m-%d'),
        'selected_department': selected_department,
        'selected_status': selected_status,
        'attendance_statuses': ExternalAttendanceLog.STATUS_CHOICES,
        'filter_options': {'departments': [d for d in departments if d]},
        'total_rows': len(rows),
        'branches': EXTERNAL_BRANCHES,
        'external_primary_url': reverse('hr:external_employee_create', args=[branch_slug]),
        'external_export_url': reverse('hr:external_attendance_export', args=[branch_slug]),
    }
    return render(request, 'hr/external_attendance.html', context)


@login_required
@hr_required
def external_attendance_create(request, branch_slug):
    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    form = ExternalAttendanceForm(request.POST or None, branch=branch_slug)
    if request.method == 'POST' and form.is_valid():
        log = form.save(commit=False)
        log.marked_by = request.user
        log.working_hours, log.late_minutes = attendance_values(log.check_in, log.check_out, log.employee)
        log.save()
        messages.success(request, 'Attendance logged.')
        return redirect('hr:external_attendance', branch_slug=branch_slug)
    return render(request, 'hr/external_attendance_form.html', {'form': form, 'branch': branch, 'external_branch_slug': branch_slug})


@login_required
@hr_required
def external_attendance_quick_update(request, branch_slug):
    from django.http import JsonResponse
    if request.method == 'POST':
        try:
            emp_id = request.POST.get('employee_id')
            date_str = request.POST.get('date')
            status = request.POST.get('status')
            remarks = request.POST.get('remarks')
            check_in_str = request.POST.get('check_in')
            check_out_str = request.POST.get('check_out')
            
            if emp_id and date_str:
                emp = hr_scope(ExternalEmployee.objects.filter(id=emp_id, branch=branch_slug), request).first()
                if emp:
                    from datetime import datetime
                    target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    log, _ = ExternalAttendanceLog.objects.get_or_create(
                        employee=emp, date=target_date, defaults={'marked_by': request.user}
                    )
                    
                    update_fields = ['marked_by', 'updated_at']
                    
                    if status:
                        log.status = status
                        update_fields.append('status')
                    if remarks is not None:
                        log.notes = remarks
                        update_fields.append('notes')
                    
                    if check_in_str is not None:
                        if check_in_str.strip():
                            log.check_in = datetime.strptime(check_in_str.strip(), '%H:%M').time() if ':' in check_in_str else None
                        else:
                            log.check_in = None
                        update_fields.append('check_in')
                        
                    if check_out_str is not None:
                        if check_out_str.strip():
                            log.check_out = datetime.strptime(check_out_str.strip(), '%H:%M').time() if ':' in check_out_str else None
                        else:
                            log.check_out = None
                        update_fields.append('check_out')

                    log.working_hours, log.late_minutes = attendance_values(log.check_in, log.check_out, emp)
                    update_fields.extend(['working_hours', 'late_minutes'])
                    log.marked_by = request.user
                    log.save(update_fields=update_fields)
                    
                    return JsonResponse({
                        'ok': True, 
                        'status': log.status, 
                        'working_hours': log.working_hours_display,
                        'check_in': log.check_in.strftime('%H:%M') if log.check_in else '',
                        'check_out': log.check_out.strftime('%H:%M') if log.check_out else ''
                    })
            return JsonResponse({'ok': False, 'error': 'Invalid parameters'})
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)})
            
    return JsonResponse({'ok': False, 'error': 'Invalid method'})


@login_required
@hr_required
def export_external_attendance(request, branch_slug):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="attendance-{branch_slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(['Employee', 'ID', 'Date', 'Login Time', 'Logout Time', 'Working Hours', 'Late', 'Status', 'Remarks'])
    base_employees = hr_scope(ExternalEmployee.objects.filter(branch=branch_slug), request)
    for log in ExternalAttendanceLog.objects.filter(employee__in=base_employees).select_related('employee').order_by('-date'):
        writer.writerow([
            log.employee.full_name,
            log.employee.employee_id,
            log.date.strftime('%d %b %Y') if log.date else '',
            log.check_in.strftime('%I:%M %p') if log.check_in else '',
            log.check_out.strftime('%I:%M %p') if log.check_out else '',
            log.working_hours_display,
            f'{log.late_minutes} min',
            log.get_status_display(),
            log.notes or '',
        ])
    return response


@login_required
@hr_required
def external_employees(request, branch_slug):
    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    query = request.GET.get('q', '').strip()
    employees = hr_scope(ExternalEmployee.objects.filter(branch=branch_slug), request)
    if query:
        employees = employees.filter(
            Q(full_name__icontains=query) | Q(employee_id__icontains=query) | Q(department__icontains=query) | Q(designation__icontains=query)
        )
    page_obj = Paginator(employees, 14).get_page(request.GET.get('page'))
    return render(request, 'hr/external_employees.html', {
        'branch': branch,
        'external_branch_slug': branch_slug,
        'page_obj': page_obj,
        'query': query,
        'total_rows': employees.count(),
        'external_primary_url': reverse('hr:external_employee_create', args=[branch_slug]),
        'external_export_url': reverse('hr:external_employee_export', args=[branch_slug]),
    })


@login_required
@hr_required
def external_employee_create(request, branch_slug):
    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    form = ExternalEmployeeForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        emp = form.save(commit=False)
        emp.branch = branch_slug
        emp.created_by = request.user
        emp.save()
        messages.success(request, 'Employee added successfully.')
        return redirect('hr:external_employees', branch_slug=branch_slug)
    return render(request, 'hr/external_employee_form.html', {'form': form, 'branch': branch, 'external_branch_slug': branch_slug, 'mode': 'add'})


@login_required
@hr_required
def external_employee_edit(request, branch_slug, employee_code):
    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    emp = get_object_or_404(hr_scope(ExternalEmployee.objects.all(), request), branch=branch_slug, employee_id=employee_code)
    form = ExternalEmployeeForm(request.POST or None, request.FILES or None, instance=emp)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Employee updated successfully.')
        return redirect('hr:external_employee_detail', branch_slug=branch_slug, employee_code=employee_code)
    return render(request, 'hr/external_employee_form.html', {'form': form, 'branch': branch, 'external_branch_slug': branch_slug, 'emp': emp, 'mode': 'edit'})


@login_required
@hr_required
def external_employee_detail(request, branch_slug, employee_code):
    import calendar
    from datetime import datetime, date
    from django.db.models import Sum

    branch = EXTERNAL_BRANCHES.get(branch_slug, EXTERNAL_BRANCHES['thane'])
    employee = get_object_or_404(hr_scope(ExternalEmployee.objects.all(), request), branch=branch_slug, employee_id=employee_code)
    
    if request.method == 'POST':
        if 'aadhaar' in request.FILES:
            employee.aadhaar = request.FILES['aadhaar']
        if 'pan' in request.FILES:
            employee.pan = request.FILES['pan']
        if 'resume' in request.FILES:
            employee.resume = request.FILES['resume']
        employee.save()
        messages.success(request, 'Documents uploaded successfully.')
        return redirect(f"{reverse('hr:external_employee_detail', args=[branch_slug, employee_code])}?tab=documents")

    today = timezone.localdate()
    selected_month = int(request.GET.get('month', today.month))
    selected_year = int(request.GET.get('year', today.year))
    selected_date_str = request.GET.get('date')

    if selected_date_str:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        selected_month = selected_date.month
        selected_year = selected_date.year
        logs = employee.attendance_logs.filter(date=selected_date).order_by('-date')
    else:
        start_date = date(selected_year, selected_month, 1)
        _, last_day = calendar.monthrange(selected_year, selected_month)
        end_date = date(selected_year, selected_month, last_day)
        logs = employee.attendance_logs.filter(date__gte=start_date, date__lte=end_date).order_by('-date')

    present = logs.filter(status='present').count()
    absent = logs.filter(status='absent').count()
    leave = logs.filter(status='leave').count()
    half_day = logs.filter(status='half_day').count()
    late = logs.filter(late_minutes__gt=0).count()
    working_days = present + half_day

    total_hours_decimal = logs.aggregate(total=Sum('working_hours'))['total'] or 0
    total_minutes = int(total_hours_decimal * 60)
    total_hours_str = f'{total_minutes // 60:02d}h {total_minutes % 60:02d}m'

    history_summary = {
        'present': present,
        'absent': absent,
        'leave': leave,
        'half_day': half_day,
        'late': late,
        'working_days': working_days,
        'total_hours': total_hours_str,
    }

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(selected_year, selected_month)
    log_dict = {log.date: log for log in logs}

    calendar_weeks = []
    for week in month_days:
        week_data = []
        for d in week:
            if d.month == selected_month:
                log = log_dict.get(d)
                if log:
                    status_code = log.get_status_display()[0].upper()
                    status_class = log.status
                else:
                    if d > today:
                        status_code = '-'
                        status_class = 'none'
                    else:
                        status_code = 'A'
                        status_class = 'absent'
                week_data.append({'day': d.day, 'code': status_code, 'status': status_class})
            else:
                week_data.append({'day': '', 'code': '', 'status': 'empty'})
        calendar_weeks.append(week_data)

    return render(request, 'hr/external_employee_detail.html', {
        'employee': employee,
        'employee_object': employee,
        'branch': branch,
        'external_branch_slug': branch_slug,
        'logs': logs,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'selected_date': selected_date_str or '',
        'history_summary': history_summary,
        'calendar_weeks': calendar_weeks,
        'month_name': calendar.month_name[selected_month],
    })


@login_required
@hr_required
def import_external_employees(request, branch_slug):
    if request.method == 'POST' and request.FILES.get('employees_file'):
        import io
        file = request.FILES['employees_file']
        decoded = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))
        created = 0
        for row in reader:
            emp_id = row.get('employee_id', '').strip()
            if emp_id and not hr_scope(ExternalEmployee.objects.filter(employee_id=emp_id), request).exists():
                ExternalEmployee.objects.create(
                    branch=branch_slug,
                    employee_id=emp_id,
                    full_name=row.get('full_name', '').strip(),
                    email=row.get('email', '').strip(),
                    mobile=row.get('mobile', '').strip(),
                    department=row.get('department', '').strip(),
                    designation=row.get('designation', '').strip(),
                    created_by=request.user,
                )
                created += 1
        messages.success(request, f'{created} employees imported.')
    return redirect('hr:external_employees', branch_slug=branch_slug)


@login_required
@hr_required
def export_external_employees(request, branch_slug):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="employees-{branch_slug}.csv"'
    writer = csv.writer(response)
    writer.writerow(['employee_id', 'full_name', 'email', 'mobile', 'department', 'designation', 'employment_type', 'status', 'joining_date'])
    for emp in hr_scope(ExternalEmployee.objects.filter(branch=branch_slug), request):
        writer.writerow([
            emp.employee_id,
            emp.full_name,
            emp.email,
            emp.mobile,
            emp.department,
            emp.designation,
            emp.get_employment_type_display(),
            emp.get_status_display(),
            emp.joining_date or '',
        ])
    return response


# ──────────────────────────────── SIMPLE SECTION ────────────────────────────────

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

# ──────────────────────────────── DELETE VIEWS ────────────────────────────────

@login_required
@hr_required
def followup_delete(request, followup_id):
    followup = get_object_or_404(hr_scope(FollowUp.objects.all(), request), id=followup_id)
    if request.method == 'POST':
        candidate_id = followup.candidate.id
        followup.delete()
        messages.success(request, 'Follow-up deleted successfully.')
        return redirect('hr:candidate_detail', candidate_id=candidate_id)
    return render(request, 'hr/confirm_delete.html', {'object': followup, 'cancel_url': reverse('hr:candidate_detail', args=[followup.candidate.id])})

@login_required
@hr_required
def interview_delete(request, interview_id):
    interview = get_object_or_404(hr_scope(Interview.objects.all(), request), id=interview_id)
    if request.method == 'POST':
        candidate_id = interview.candidate.id
        interview.delete()
        messages.success(request, 'Interview deleted successfully.')
        return redirect('hr:candidate_detail', candidate_id=candidate_id)
    return render(request, 'hr/confirm_delete.html', {'object': interview, 'cancel_url': reverse('hr:candidate_detail', args=[interview.candidate.id])})

@login_required
@hr_required
def placement_drive_delete(request, drive_id):
    drive = get_object_or_404(hr_scope(PlacementDrive.objects.all(), request), id=drive_id)
    if request.method == 'POST':
        drive.delete()
        messages.success(request, 'Placement drive deleted successfully.')
        return redirect('hr:placement_drive_list')
    return render(request, 'hr/confirm_delete.html', {'object': drive, 'cancel_url': reverse('hr:placement_drive_list')})

@login_required
@hr_required
def placement_batch_delete(request, batch_id):
    batch = get_object_or_404(PlacementBatch, id=batch_id)
    if request.method == 'POST':
        batch.delete()
        messages.success(request, 'Placement batch deleted successfully.')
        return redirect('hr:placement_batch_list')
    return render(request, 'hr/confirm_delete.html', {'object': batch, 'cancel_url': reverse('hr:placement_batch_list')})

@login_required
@hr_required
def placement_assignment_delete(request, assignment_id):
    assignment = get_object_or_404(hr_scope(PlacementStudentAssignment.objects.all(), request), id=assignment_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Assignment deleted successfully.')
        return redirect('hr:placement_student_list')
    return render(request, 'hr/confirm_delete.html', {'object': assignment, 'cancel_url': reverse('hr:placement_assignment_detail', args=[assignment.id])})

@login_required
@hr_required
def placement_interview_delete(request, interview_id):
    interview = get_object_or_404(hr_scope(PlacementInterview.objects.all(), request), id=interview_id)
    if request.method == 'POST':
        interview.delete()
        messages.success(request, 'Placement interview deleted successfully.')
        return redirect('hr:placement_interview_list')
    return render(request, 'hr/confirm_delete.html', {'object': interview, 'cancel_url': reverse('hr:placement_interview_list')})

@login_required
@hr_required
def placement_offer_delete(request, offer_id):
    offer = get_object_or_404(hr_scope(PlacementOffer.objects.all(), request), id=offer_id)
    if request.method == 'POST':
        offer.delete()
        messages.success(request, 'Offer deleted successfully.')
        return redirect('hr:placement_offer_list')
    return render(request, 'hr/confirm_delete.html', {'object': offer, 'cancel_url': reverse('hr:placement_offer_list')})

@login_required
@hr_required
def external_employee_delete(request, branch_slug, employee_code):
    employee = get_object_or_404(hr_scope(ExternalEmployee.objects.all(), request), branch=branch_slug, employee_id=employee_code)
    if request.method == 'POST':
        employee.delete()
        messages.success(request, 'Employee deleted successfully.')
        return redirect('hr:external_employees', branch_slug=branch_slug)
    return render(request, 'hr/confirm_delete.html', {'object': employee, 'cancel_url': reverse('hr:external_employee_detail', args=[branch_slug, employee_code])})

@login_required
@hr_required
def project_company_delete(request, company_id):
    company = get_object_or_404(hr_scope(ProjectCompany.objects.all(), request), id=company_id)
    if request.method == 'POST':
        company.delete()
        messages.success(request, 'Project company deleted successfully.')
        return redirect('hr:project_company_list')
    return render(request, 'hr/confirm_delete.html', {'object': company, 'cancel_url': reverse('hr:project_company_detail', args=[company.id])})

@login_required
@hr_required
def project_drive_delete(request, drive_id):
    drive = get_object_or_404(hr_scope(ProjectDrive.objects.all(), request), id=drive_id)
    if request.method == 'POST':
        drive.delete()
        messages.success(request, 'Project drive deleted successfully.')
        return redirect('hr:project_drive_list')
    return render(request, 'hr/confirm_delete.html', {'object': drive, 'cancel_url': reverse('hr:project_drive_detail', args=[drive.id])})

@login_required
@hr_required
def project_assignment_delete(request, assignment_id):
    assignment = get_object_or_404(hr_scope(ProjectEmployeeAssignment.objects.all(), request), id=assignment_id)
    if request.method == 'POST':
        assignment.delete()
        messages.success(request, 'Assignment deleted successfully.')
        return redirect('hr:project_employee_list')
    return render(request, 'hr/confirm_delete.html', {'object': assignment, 'cancel_url': reverse('hr:project_assignment_detail', args=[assignment.id])})

@login_required
@hr_required
def project_interview_delete(request, interview_id):
    interview = get_object_or_404(hr_scope(ProjectInterview.objects.all(), request), id=interview_id)
    if request.method == 'POST':
        interview.delete()
        messages.success(request, 'Project interview deleted successfully.')
        return redirect('hr:project_interview_list')
    return render(request, 'hr/confirm_delete.html', {'object': interview, 'cancel_url': reverse('hr:project_interview_list')})

@login_required
@hr_required
def project_allocation_delete(request, allocation_id):
    allocation = get_object_or_404(hr_scope(ProjectAllocation.objects.all(), request), id=allocation_id)
    if request.method == 'POST':
        allocation.delete()
        messages.success(request, 'Allocation deleted successfully.')
        return redirect('hr:project_allocation_list')
    return render(request, 'hr/confirm_delete.html', {'object': allocation, 'cancel_url': reverse('hr:project_allocation_list')})


# ───────────────────────────── PLACEMENT WORKFLOW ─────────────────────────────

placement_signer = TimestampSigner(salt='placement-resume-upload')


def _placement_student_email(assignment):
    if assignment.batch_student and assignment.batch_student.email:
        return assignment.batch_student.email
    if assignment.student and assignment.student.email:
        return assignment.student.email
    return ''


def _placement_resume_token(assignment):
    return placement_signer.sign(str(assignment.id))


def _placement_resume_url(request, assignment):
    return request.build_absolute_uri(reverse('hr:placement_resume_upload', args=[_placement_resume_token(assignment)]))


def _placement_render_body(body, assignment, request=None):
    company = assignment.drive.company if assignment.drive else assignment.company
    replacements = {
        '{{student_name}}': assignment.display_name,
        '{{company_name}}': company.name if company else '',
        '{{job_role}}': assignment.drive.job_role if assignment.drive else '',
        '{{resume_upload_link}}': _placement_resume_url(request, assignment) if request else '',
        '{{final_status}}': assignment.get_final_status_display(),
        '{{offered_role}}': assignment.offered_role,
        '{{offered_ctc}}': assignment.offered_ctc,
    }
    for key, value in replacements.items():
        body = body.replace(key, value or '')
    return body


def _placement_log_email(drive, email_type, recipient, subject, status, request=None, assignment=None, error=''):
    return PlacementEmailLog.objects.create(
        drive=drive,
        assignment=assignment,
        email_type=email_type,
        recipient_email=recipient or '',
        subject=subject,
        status=status,
        error_message=error,
        sent_at=timezone.now() if status == 'sent' else None,
        created_by=request.user if request and request.user.is_authenticated else None,
    )


def _placement_email_config_error():
    return EmailConfigurationService.configuration_error()


def _placement_send_email(drive, email_type, recipient, subject, body, request=None, assignment=None, attachments=None):
    if not recipient:
        return _placement_log_email(drive, email_type, recipient, subject, 'skipped', request, assignment, 'Missing recipient email.')
    config_error = _placement_email_config_error()
    if config_error:
        return _placement_log_email(drive, email_type, recipient, subject, 'failed', request, assignment, config_error)
    try:
        EmailConfigurationService.send_mail(subject, body, [recipient], attachments=attachments)
    except (EmailDeliveryError, OSError) as exc:
        return _placement_log_email(drive, email_type, recipient, subject, 'failed', request, assignment, str(exc))
    return _placement_log_email(drive, email_type, recipient, subject, 'sent', request, assignment)


def _placement_headers(row):
    mapping = {}
    aliases = {
        'full_name': {'student name', 'name', 'full name', 'candidate name'},
        'email': {'email', 'mail id', 'email id', 'mail'},
        'mobile': {'mobile', 'phone', 'contact no', 'contact no 1', 'contact number', 'contact number 1', 'whatsapp number'},
        'alternate_mobile': {'contact no 2', 'contact number 2', 'alternate mobile', 'alternate contact', 'secondary contact'},
    }
    for index, value in enumerate(row):
        key = re.sub(r'\s+', ' ', candidate_text(value).lower()).strip()
        for field, names in aliases.items():
            if key in names:
                mapping[index] = field
    return mapping


def _placement_generate_enrollment_no(batch):
    year_match = re.search(r'\d{4}', batch.academic_year or '')
    year = year_match.group(0) if year_match else str(timezone.now().year)
    prefix = f'PLC{year}'
    existing_numbers = []
    for value in batch.students.filter(enrollment_no__startswith=prefix).values_list('enrollment_no', flat=True):
        suffix = value.replace(prefix, '', 1)
        if suffix.isdigit():
            existing_numbers.append(int(suffix))
    next_number = (max(existing_numbers) if existing_numbers else 0) + 1
    return f'{prefix}{next_number:03d}'


def _placement_student_profile(enrollment_no, full_name, email, mobile):
    admission = StudentAdmission.objects.filter(enrollment_no__iexact=enrollment_no).select_related('user').first()
    if admission and admission.user:
        profile = StudentProfile.objects.filter(user=admission.user).first()
        if profile:
            return profile
    user = User.objects.filter(username__iexact=enrollment_no).first()
    if not user:
        user = User.objects.create_user(
            username=enrollment_no,
            email=email or f'{enrollment_no}@example.com',
            password=None,
            role='student',
            is_active=True,
        )
        user.set_unusable_password()
        user.save(update_fields=['password'])
    profile, _ = StudentProfile.objects.get_or_create(
        user=user,
        defaults={
            'full_name': full_name,
            'email': email or user.email or f'{enrollment_no}@example.com',
            'phone': mobile,
        },
    )
    updates = []
    if full_name and profile.full_name != full_name:
        profile.full_name = full_name
        updates.append('full_name')
    if email and profile.email != email:
        profile.email = email
        updates.append('email')
    if mobile and profile.phone != mobile:
        profile.phone = mobile
        updates.append('phone')
    if updates:
        profile.save(update_fields=updates)
    return profile


def _placement_create_assignments_for_drive(drive, request):
    created = 0
    for batch_student in PlacementBatchStudent.objects.filter(batch__in=drive.batches.all()).select_related('student', 'batch'):
        assignment, was_created = PlacementStudentAssignment.objects.get_or_create(
            drive=drive,
            batch_student=batch_student,
            defaults={
                'company': drive.company,
                'student': batch_student.student,
                'student_name': batch_student.full_name,
                'course_name': batch_student.course_name,
                'resume_status': 'pending',
                'assigned_by': request.user,
            },
        )
        if was_created:
            created += 1
        else:
            assignment.company = drive.company
            assignment.student = batch_student.student
            assignment.student_name = batch_student.full_name
            assignment.course_name = batch_student.course_name
            assignment.save(update_fields=['company', 'student', 'student_name', 'course_name', 'updated_at'])
    return created


@login_required
@hr_required
def placement_dashboard(request):
    drives = PlacementDrive.objects.select_related('company').prefetch_related('batches').order_by('-created_at')[:6]
    context = {
        'batches_count': PlacementBatch.objects.count(),
        'companies_count': PlacementCompany.objects.count(),
        'drives_count': PlacementDrive.objects.count(),
        'resume_pending_count': PlacementStudentAssignment.objects.exclude(resume_status='submitted').count(),
        'selected_count': PlacementStudentAssignment.objects.filter(final_status='selected').count(),
        'drives': drives,
        'activities': PlacementActivity.objects.select_related('company', 'drive', 'created_by')[:8],
        'email_logs': PlacementEmailLog.objects.select_related('drive')[:8],
    }
    return render(request, 'hr/placement_workflow_dashboard.html', context)


@login_required
@hr_required
def placement_batch_list(request):
    query = request.GET.get('q', '').strip()
    year = request.GET.get('year', '').strip()
    batches = PlacementBatch.objects.select_related('course').annotate(student_total=Count('students')).order_by('-created_at', 'name')
    year_options = (
        PlacementBatch.objects.exclude(academic_year='')
        .values_list('academic_year', flat=True)
        .distinct()
        .order_by('-academic_year')
    )
    if query:
        batches = batches.filter(
            Q(name__icontains=query)
            | Q(course__name__icontains=query)
            | Q(academic_year__icontains=query)
        )
    if year:
        batches = batches.filter(academic_year=year)

    paginator = Paginator(batches, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    all_batches = PlacementBatch.objects.annotate(student_total=Count('students'))
    context = {
        'batches': page_obj.object_list,
        'page_obj': page_obj,
        'query': query,
        'selected_year': year,
        'year_options': year_options,
        'total_batches': all_batches.count(),
        'total_students': sum(batch.student_total for batch in all_batches),
        'academic_years_count': PlacementBatch.objects.exclude(academic_year='').values('academic_year').distinct().count(),
        'active_batches': all_batches.count(),
    }
    return render(request, 'hr/placement_batch_list.html', context)


@login_required
@hr_required
def placement_batch_create(request):
    form = PlacementBatchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        batch = form.save(commit=False)
        batch.created_by = request.user
        batch.save()
        PlacementActivity.objects.create(activity_type='batch', title='Batch Created', description=str(batch), created_by=request.user)
        messages.success(request, 'Placement batch saved.')
        return redirect('hr:placement_batch_detail', batch_id=batch.id)
    return render(request, 'hr/placement_form.html', {'form': form, 'title': 'Create Batch', 'cancel_url': reverse('hr:placement_batch_list')})


@login_required
@hr_required
def placement_batch_detail(request, batch_id):
    batch = get_object_or_404(PlacementBatch.objects.select_related('course'), id=batch_id)
    students = batch.students.select_related('student')[:200]
    imports = batch.imports.select_related('imported_by')[:10]
    return render(request, 'hr/placement_batch_detail.html', {'batch': batch, 'students': students, 'imports': imports})


@login_required
@hr_required
def placement_batch_student_history(request, batch_id, student_id):
    batch = get_object_or_404(PlacementBatch.objects.select_related('course'), id=batch_id)
    batch_student = get_object_or_404(
        PlacementBatchStudent.objects.select_related('student', 'batch', 'batch__course'),
        id=student_id,
        batch=batch,
    )
    lead_history = (
        PlacementStudentAssignment.objects
        .filter(batch_student=batch_student)
        .select_related('drive', 'drive__company', 'company')
        .order_by('-drive__drive_date', '-assigned_at')
    )
    return render(request, 'hr/placement_batch_student_history.html', {
        'batch': batch,
        'student': batch_student,
        'lead_history': lead_history,
        'lead_count': lead_history.count(),
    })


@login_required
@hr_required
def placement_student_template(request, batch_id):
    batch = get_object_or_404(PlacementBatch, id=batch_id)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{batch.name}-students-template.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Email ID', 'Contact No 1', 'Contact No 2'])
    return response


@login_required
@hr_required
def placement_import_students(request, batch_id):
    batch = get_object_or_404(PlacementBatch, id=batch_id)
    form = PlacementBatchImportForm(request.POST or None, request.FILES or None)
    row_errors = []
    if request.method == 'POST' and form.is_valid():
        rows = candidate_import_rows(form.cleaned_data['students_file'])
        header_index = None
        header_map = {}
        for index, row in enumerate(rows):
            mapped = _placement_headers(row)
            if {'full_name', 'email', 'mobile', 'alternate_mobile'}.issubset(set(mapped.values())):
                header_index = index
                header_map = mapped
                break
        if header_index is None:
            messages.error(request, 'Import failed. Required columns: Name, Email ID, Contact No 1, Contact No 2.')
        else:
            imported = skipped = failed = 0
            for row_number, row in enumerate(rows[header_index + 1:], start=header_index + 2):
                data = {field: candidate_text(row[index]) if index < len(row) else '' for index, field in header_map.items()}
                full_name = data.get('full_name', '')
                email = data.get('email', '')
                mobile = data.get('mobile', '')
                alternate_mobile = data.get('alternate_mobile', '')
                course_name = batch.course.name if batch.course else ''
                if not full_name or not email or not mobile:
                    failed += 1
                    row_errors.append(f'Row {row_number}: Name, Email ID and Contact No 1 are required.')
                    continue
                if PlacementBatchStudent.objects.filter(batch=batch).filter(Q(email__iexact=email) | Q(mobile__iexact=mobile)).exists():
                    skipped += 1
                    continue
                enrollment_no = _placement_generate_enrollment_no(batch)
                profile = _placement_student_profile(enrollment_no, full_name, email, mobile)
                PlacementBatchStudent.objects.create(
                    batch=batch,
                    student=profile,
                    enrollment_no=enrollment_no,
                    full_name=full_name,
                    email=email,
                    mobile=mobile,
                    alternate_mobile=alternate_mobile,
                    course_name=course_name,
                    imported_by=request.user,
                )
                imported += 1
            summary = f'Imported: {imported}, Skipped: {skipped}, Failed: {failed}'
            PlacementBatchImport.objects.create(
                batch=batch,
                imported_by=request.user,
                imported_count=imported,
                skipped_count=skipped,
                failed_count=failed,
                summary=summary,
                errors='\n'.join(row_errors),
            )
            PlacementActivity.objects.create(activity_type='batch', title='Students Imported', description=summary, created_by=request.user)
            messages.success(request, summary)
            return redirect('hr:placement_batch_detail', batch_id=batch.id)
    return render(request, 'hr/placement_import_students.html', {'batch': batch, 'form': form, 'row_errors': row_errors})


@login_required
@hr_required
def placement_company_list(request):
    base_companies = PlacementCompany.objects.all()
    query = request.GET.get('q', '').strip()
    selected_role = request.GET.get('role', '').strip()
    selected_location = request.GET.get('location', '').strip()

    companies = base_companies.order_by('-updated_at')
    if query:
        companies = companies.filter(
            Q(name__icontains=query)
            | Q(contact_person__icontains=query)
            | Q(email__icontains=query)
            | Q(mobile__icontains=query)
            | Q(job_role__icontains=query)
            | Q(location__icontains=query)
        )
    if selected_role:
        companies = companies.filter(job_role=selected_role)
    if selected_location:
        companies = companies.filter(location=selected_location)

    page_obj = Paginator(companies, 6).get_page(request.GET.get('page'))
    query_params = request.GET.copy()
    query_params.pop('page', None)
    context = {
        'companies': page_obj.object_list,
        'page_obj': page_obj,
        'query': query,
        'selected_role': selected_role,
        'selected_location': selected_location,
        'role_options': base_companies.exclude(job_role='').order_by('job_role').values_list('job_role', flat=True).distinct(),
        'location_options': base_companies.exclude(location='').order_by('location').values_list('location', flat=True).distinct(),
        'page_query': query_params.urlencode(),
    }
    return render(request, 'hr/placement_company_list.html', context)


@login_required
@hr_required
def placement_company_create(request):
    form = PlacementCompanyForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        company = form.save(commit=False)
        company.created_by = request.user
        company.save()
        PlacementActivity.objects.create(activity_type='company', title='Company Created', description=company.name, company=company, created_by=request.user)
        messages.success(request, 'Company saved.')
        return redirect('hr:placement_company_detail', company_id=company.id)
    return render(request, 'hr/placement_form.html', {'form': form, 'title': 'Create Company', 'cancel_url': reverse('hr:placement_company_list')})


@login_required
@hr_required
def placement_company_edit(request, company_id):
    company = get_object_or_404(PlacementCompany, id=company_id)
    form = PlacementCompanyForm(request.POST or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Company updated.')
        return redirect('hr:placement_company_detail', company_id=company.id)
    return render(request, 'hr/placement_form.html', {'form': form, 'title': 'Edit Company', 'cancel_url': reverse('hr:placement_company_detail', args=[company.id])})


@login_required
@hr_required
def placement_company_detail(request, company_id):
    company = get_object_or_404(PlacementCompany, id=company_id)
    drives = company.drives.prefetch_related('batches').order_by('-created_at')
    drive_list = list(drives)
    for drive in drive_list:
        drive.sent_count = drive.eligible_count
    paginator = Paginator(drive_list, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    summary = {
        'total_drives': len(drive_list),
        'eligible_students': sum(drive.eligible_count for drive in drive_list),
        'resumes_received': sum(drive.resume_submitted_count for drive in drive_list),
        'shortlisted': sum(drive.shortlisted_count for drive in drive_list),
        'selected': sum(drive.selected_count for drive in drive_list),
    }
    return render(request, 'hr/placement_company_detail.html', {
        'company': company,
        'drives': page_obj.object_list,
        'summary': summary,
        'page_obj': page_obj,
        'paginator': paginator,
    })


@login_required
@hr_required
def placement_drive_list(request):
    drives = PlacementDrive.objects.select_related('company').prefetch_related('batches').order_by('-created_at')
    paginator = Paginator(drives, 5)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'hr/placement_drive_list.html', {
        'drives': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
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
        if drive.company:
            if not drive.job_role:
                drive.job_role = drive.company.job_role
            drive.eligibility_criteria = drive.company.required_skills
            drive.venue = drive.company.location
            drive.remarks = drive.company.additional_job_details
        drive.status = 'scheduled'
        drive.created_by = request.user
        drive.save()
        form.save_m2m()
        created = _placement_create_assignments_for_drive(drive, request)
        PlacementActivity.objects.create(activity_type='drive', title='Placement Drive Created', description=f'{created} eligible students fetched.', company=drive.company, drive=drive, created_by=request.user)
        messages.success(request, f'Placement drive created. Eligible students: {drive.eligible_count}.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_drive_form_custom.html', {'form': form, 'title': 'Create Placement Drive', 'cancel_url': reverse('hr:placement_drive_list')})


@login_required
@hr_required
def placement_drive_edit(request, drive_id):
    drive = get_object_or_404(PlacementDrive, id=drive_id)
    form = PlacementDriveForm(request.POST or None, instance=drive)
    if request.method == 'POST' and form.is_valid():
        drive = form.save()
        created = _placement_create_assignments_for_drive(drive, request)
        messages.success(request, f'Drive updated. New eligible students added: {created}.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_drive_form_custom.html', {'form': form, 'title': 'Edit Placement Drive', 'cancel_url': reverse('hr:placement_drive_detail', args=[drive.id])})


@login_required
@hr_required
def placement_drive_detail(request, drive_id):
    drive = get_object_or_404(PlacementDrive.objects.select_related('company').prefetch_related('batches'), id=drive_id)
    assignments = drive.assignments.select_related('batch_student', 'student').order_by('student_name')
    return render(request, 'hr/placement_drive_detail.html', {'drive': drive, 'assignments': assignments, 'email_logs': drive.email_logs.all()[:12]})


@login_required
@hr_required
def placement_create_email(request, drive_id, email_type):
    drive = get_object_or_404(PlacementDrive.objects.select_related('company'), id=drive_id)
    defaults = {
        'resume_request': ('Resume required for placement drive', 'Dear {{student_name}},\n\nPlease upload your latest resume for {{company_name}} - {{job_role}} using this link:\n{{resume_upload_link}}\n\nRegards,\nHR Team'),
        'interview': ('Interview update for placement drive', 'Dear {{student_name}},\n\nYou are shortlisted for {{company_name}} - {{job_role}}. Interview details will be shared by HR.\n\nRegards,\nHR Team'),
        'final_result': ('Placement result update', 'Dear {{student_name}},\n\nYour final status for {{company_name}} - {{job_role}} is {{final_status}}.\nOffered Role: {{offered_role}}\nCTC: {{offered_ctc}}\n\nRegards,\nHR Team'),
    }
    if email_type not in defaults:
        messages.error(request, 'Invalid email action.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)

    def email_recipients():
        if email_type == 'resume_request':
            return drive.assignments.select_related('batch_student', 'student')
        if email_type == 'interview':
            return drive.assignments.filter(is_shortlisted=True).select_related('batch_student', 'student')
        return drive.assignments.filter(final_status__in=['selected', 'rejected', 'on_hold']).select_related('batch_student', 'student')

    draft_key = f'placement_email_draft_{drive.id}_{email_type}'
    initial = request.session.get(draft_key, {'subject': defaults[email_type][0], 'body': defaults[email_type][1]})
    form = PlacementEmailForm(request.POST or None, initial=initial)
    recipients = email_recipients()
    if request.method == 'POST' and form.is_valid():
        subject = form.cleaned_data['subject']
        body = form.cleaned_data['body']
        if request.POST.get('action') == 'draft':
            request.session[draft_key] = {'subject': subject, 'body': body}
            request.session.modified = True
            messages.success(request, 'Email draft saved.')
            return redirect('hr:placement_create_email', drive_id=drive.id, email_type=email_type)

        recipients = email_recipients()
        sent = failed = skipped = 0
        for assignment in recipients:
            log = _placement_send_email(
                drive,
                email_type,
                _placement_student_email(assignment),
                subject,
                _placement_render_body(body, assignment, request),
                request,
                assignment,
            )
            if email_type == 'resume_request' and log.status == 'sent':
                assignment.resume_status = 'requested'
                assignment.save(update_fields=['resume_status', 'updated_at'])
            sent += log.status == 'sent'
            failed += log.status == 'failed'
            skipped += log.status == 'skipped'
        if sent:
            if email_type == 'resume_request':
                drive.status = 'resume_requested'
            elif email_type == 'interview':
                drive.status = 'interviewing'
            else:
                drive.status = 'completed'
            drive.save(update_fields=['status', 'updated_at'])
        request.session.pop(draft_key, None)
        PlacementActivity.objects.create(activity_type='email', title='Email Sent', description=f'{sent} sent, {failed} failed, {skipped} skipped.', company=drive.company, drive=drive, created_by=request.user)
        result_message = f'Email processed. Sent: {sent}, Failed: {failed}, Skipped: {skipped}.'
        if sent:
            messages.success(request, result_message)
        else:
            messages.error(request, result_message)
        return redirect('hr:placement_drive_detail', drive_id=drive.id)

    recipient_rows = [
        {
            'name': assignment.display_name,
            'email': _placement_student_email(assignment),
            'course': assignment.display_course or '',
            'status': assignment.get_resume_status_display() if email_type == 'resume_request' else assignment.assignment_status_display,
        }
        for assignment in recipients
    ]
    preview_assignment = recipients.first()
    preview_body = _placement_render_body(form.initial.get('body', ''), preview_assignment, request) if preview_assignment else ''
    return render(request, 'hr/placement_email_form.html', {
        'drive': drive,
        'form': form,
        'email_type': email_type,
        'recipient_rows': recipient_rows,
        'recipient_count': len(recipient_rows),
        'preview_body': preview_body,
        'draft_saved': draft_key in request.session,
        'email_config_error': _placement_email_config_error(),
    })


@login_required
@hr_required
def placement_send_resumes_to_company(request, drive_id):
    drive = get_object_or_404(PlacementDrive.objects.select_related('company'), id=drive_id)
    assignments = list(drive.assignments.filter(resume_status='submitted').exclude(resume=''))
    attachments = [assignment.resume.path for assignment in assignments if assignment.resume]
    subject = f'Resumes for {drive.job_role or "Placement Drive"}'
    body = f'Please find submitted resumes for {drive.company.name if drive.company else "the placement drive"}.\n\nTotal resumes: {len(attachments)}'
    log = _placement_send_email(drive, 'company_resumes', drive.company.email if drive.company else '', subject, body, request, attachments=attachments)
    if log.status == 'sent':
        drive.status = 'resumes_sent'
        drive.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'Resumes to company status: {log.get_status_display()}.')
    else:
        messages.error(request, log.error_message or f'Resumes to company status: {log.get_status_display()}.')
    return redirect('hr:placement_drive_detail', drive_id=drive.id)


@login_required
@hr_required
def email_configuration(request):
    config = EmailConfiguration.active() or EmailConfiguration.objects.order_by('-updated_at').first()
    form = EmailConfigurationForm(request.POST or None, instance=config)
    if request.method == 'POST' and form.is_valid():
        config = form.save()
        if request.POST.get('action') == 'test':
            try:
                EmailConfigurationService.send_mail(
                    'Email configuration test',
                    'This is a test email from your Placement Management System email configuration.',
                    [config.email_address],
                )
            except EmailDeliveryError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f'Test email sent successfully to {config.email_address}.')
        else:
            messages.success(request, 'Email configuration saved successfully.')
        return redirect('hr:email_configuration')
    return render(request, 'hr/email_configuration.html', {
        'form': form,
        'config': config,
        'has_password': bool(config and config.google_app_password),
    })


@login_required
@hr_required
def placement_update_shortlist(request, drive_id):
    drive = get_object_or_404(PlacementDrive, id=drive_id)
    assignments = drive.assignments.select_related('batch_student', 'student')
    if request.method == 'POST':
        selected_ids = set(request.POST.getlist('shortlisted'))
        for assignment in assignments:
            assignment.is_shortlisted = str(assignment.id) in selected_ids
            assignment.save(update_fields=['is_shortlisted', 'updated_at'])
        PlacementActivity.objects.create(activity_type='result', title='Shortlist Updated', description=f'{len(selected_ids)} students shortlisted.', drive=drive, company=drive.company, created_by=request.user)
        messages.success(request, 'Shortlist updated.')
        return redirect('hr:placement_update_shortlist', drive_id=drive.id)
    return render(request, 'hr/placement_shortlist.html', {'drive': drive, 'assignments': assignments})


@login_required
@hr_required
def placement_update_attendance(request, drive_id):
    drive = get_object_or_404(PlacementDrive, id=drive_id)
    assignments = drive.assignments.filter(is_shortlisted=True).select_related('batch_student', 'student')
    if request.method == 'POST':
        for assignment in assignments:
            value = request.POST.get(f'attendance_{assignment.id}', 'pending')
            if value in {'present', 'absent', 'pending'}:
                assignment.interview_attendance = value
                assignment.save(update_fields=['interview_attendance', 'updated_at'])
        messages.success(request, 'Interview attendance saved.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_attendance.html', {'drive': drive, 'assignments': assignments})


@login_required
@hr_required
def placement_update_results(request, drive_id):
    drive = get_object_or_404(PlacementDrive, id=drive_id)
    assignments = drive.assignments.filter(interview_attendance='present').select_related('batch_student', 'student')
    if request.method == 'POST':
        for assignment in assignments:
            status = request.POST.get(f'status_{assignment.id}', 'pending')
            if status in {'pending', 'selected', 'rejected', 'on_hold'}:
                assignment.final_status = status
                assignment.offered_role = request.POST.get(f'role_{assignment.id}', '').strip() if status == 'selected' else ''
                assignment.offered_ctc = request.POST.get(f'ctc_{assignment.id}', '').strip() if status == 'selected' else ''
                assignment.save(update_fields=['final_status', 'offered_role', 'offered_ctc', 'updated_at'])
                if status == 'selected':
                    PlacementOffer.objects.update_or_create(
                        assignment=assignment,
                        defaults={
                            'company': drive.company,
                            'offered_package': assignment.offered_ctc,
                            'offer_status': 'offered',
                            'joining_status': 'awaiting',
                            'created_by': request.user,
                        },
                    )
        PlacementActivity.objects.create(activity_type='result', title='Final Results Updated', description='Final placement results saved.', drive=drive, company=drive.company, created_by=request.user)
        messages.success(request, 'Final results saved.')
        return redirect('hr:placement_drive_detail', drive_id=drive.id)
    return render(request, 'hr/placement_results.html', {'drive': drive, 'assignments': assignments})


def placement_resume_upload(request, token):
    try:
        assignment_id = placement_signer.unsign(token, max_age=60 * 60 * 24 * 30)
    except (BadSignature, SignatureExpired):
        return render(request, 'hr/placement_resume_upload.html', {'invalid_link': True})
    assignment = get_object_or_404(PlacementStudentAssignment.objects.select_related('drive', 'drive__company', 'batch_student'), id=assignment_id)
    if request.method == 'POST':
        resume = request.FILES.get('resume')
        if not resume:
            messages.error(request, 'Please choose a resume file.')
        else:
            assignment.resume = resume
            assignment.resume_status = 'submitted'
            assignment.resume_submitted_at = timezone.now()
            assignment.save(update_fields=['resume', 'resume_status', 'resume_submitted_at', 'updated_at'])
            PlacementActivity.objects.create(activity_type='resume', title='Resume Submitted', description=assignment.display_name, drive=assignment.drive, company=assignment.company)
            return render(request, 'hr/placement_resume_upload.html', {'assignment': assignment, 'submitted': True})
    return render(request, 'hr/placement_resume_upload.html', {'assignment': assignment})


@login_required
@hr_required
def placement_student_list(request):
    return redirect('hr:placement_drive_list')


@login_required
@hr_required
def placement_offer_list(request):
    return redirect('hr:placement_drive_list')


