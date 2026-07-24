from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FraudTypeForm, PoliceStationForm
from .models import FraudType, PoliceStation


def investigator_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role in ('admin', 'investigator'):
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Investigator Panel only.")
    return wrapper


def investigator_admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Admins only.")
    return wrapper


def render_panel_page(request, title, description, phase_note, admin_only=False, primary_action=None):
    return render(request, 'investigator/panel_page.html', {
        'title': title,
        'description': description,
        'phase_note': phase_note,
        'admin_only': admin_only,
        'primary_action': primary_action,
    })


@login_required
@investigator_required
def investigator_dashboard(request):
    return render(request, 'investigator/dashboard.html')


@login_required
@investigator_required
def recovery_reports(request):
    title = 'Recovery Reports' if request.user.role == 'admin' else 'My Recovery Reports'
    description = 'Recovery report listing and entry page placeholder.'
    return render_panel_page(
        request,
        title,
        description,
        'Form and listing will be built in Phase 4 and Phase 5.',
        primary_action={
            'url_name': 'investigator_recovery_add',
            'label': 'Add Recovery Report',
            'icon': 'bi-plus-circle',
        },
    )


@login_required
@investigator_required
def recovery_report_add(request):
    return render_panel_page(
        request,
        'Add Recovery Report',
        'Investigator recovery report form placeholder.',
        'The actual recovery form fields will be built in Phase 4.'
    )


@login_required
@investigator_required
def case_work_reports(request):
    title = 'Case Work Reports' if request.user.role == 'admin' else 'My Case Work Reports'
    description = 'Case work report listing and entry page placeholder.'
    return render_panel_page(
        request,
        title,
        description,
        'Form and listing will be built in Phase 6 and Phase 7.',
        primary_action={
            'url_name': 'investigator_case_work_add',
            'label': 'Add Case Work Report',
            'icon': 'bi-file-earmark-plus',
        },
    )


@login_required
@investigator_required
def case_work_report_add(request):
    return render_panel_page(
        request,
        'Add Case Work Report',
        'Investigator case work report form placeholder.',
        'The multi-work-description form will be built in Phase 6.'
    )


@login_required
@investigator_admin_required
def student_wise_report(request):
    return render_panel_page(
        request,
        'Student-wise Report',
        'Admin report page placeholder for one student investigation history.',
        'Student-wise reporting will be built in Phase 9.',
        admin_only=True,
    )


@login_required
@investigator_admin_required
def universal_report(request):
    return render_panel_page(
        request,
        'Universal Report',
        'Admin report page placeholder for approved investigation data.',
        'Universal reporting will be built in Phase 10.',
        admin_only=True,
    )


@login_required
@investigator_admin_required
def approval_review(request):
    return render_panel_page(
        request,
        'Approval / Review',
        'Admin approval and rejection page placeholder.',
        'Approval workflow will become active after report forms are built.',
        admin_only=True,
    )


@login_required
@investigator_admin_required
def master_settings(request):
    return render(request, 'investigator/master_settings.html')


@login_required
@investigator_admin_required
def export_print(request):
    return render_panel_page(
        request,
        'Export / Print',
        'Admin export and print page placeholder.',
        'Export buttons will be built in Phase 11.',
        admin_only=True,
    )


def master_list_view(request, model, form_class, template_name, redirect_name, title, description):
    form = form_class()
    if request.method == 'POST':
        form = form_class(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'{title} "{item.name}" added successfully.')
            return redirect(redirect_name)

    query = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    items = model.objects.all().order_by('name')

    if query:
        items = items.filter(Q(name__icontains=query))
    if status == 'active':
        items = items.filter(is_active=True)
    elif status == 'inactive':
        items = items.filter(is_active=False)

    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, template_name, {
        'form': form,
        'page_obj': page_obj,
        'query': query,
        'status': status,
        'title': title,
        'description': description,
        'redirect_name': redirect_name,
    })


def master_edit_view(request, pk, model, form_class, template_name, redirect_name, title):
    item = get_object_or_404(model, pk=pk)
    if request.method == 'POST':
        form = form_class(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'{title} "{item.name}" updated successfully.')
            return redirect(redirect_name)
    else:
        form = form_class(instance=item)

    return render(request, template_name, {
        'form': form,
        'item': item,
        'title': title,
        'redirect_name': redirect_name,
    })


def master_toggle_view(request, pk, model, redirect_name, title):
    if request.method != 'POST':
        return HttpResponseForbidden("Invalid request.")

    item = get_object_or_404(model, pk=pk)
    item.is_active = not item.is_active
    item.save(update_fields=['is_active', 'updated_at'])
    status = 'activated' if item.is_active else 'deactivated'
    messages.success(request, f'{title} "{item.name}" {status} successfully.')
    return redirect(redirect_name)


@login_required
@investigator_admin_required
def fraud_type_list(request):
    return master_list_view(
        request,
        FraudType,
        FraudTypeForm,
        'investigator/master_list.html',
        'investigator_fraud_type_list',
        'Fraud Type',
        'Manage fraud type dropdown values for recovery reports.',
    )


@login_required
@investigator_admin_required
def fraud_type_edit(request, pk):
    return master_edit_view(
        request,
        pk,
        FraudType,
        FraudTypeForm,
        'investigator/master_edit.html',
        'investigator_fraud_type_list',
        'Fraud Type',
    )


@login_required
@investigator_admin_required
def fraud_type_toggle(request, pk):
    return master_toggle_view(request, pk, FraudType, 'investigator_fraud_type_list', 'Fraud Type')


@login_required
@investigator_admin_required
def police_station_list(request):
    return master_list_view(
        request,
        PoliceStation,
        PoliceStationForm,
        'investigator/master_list.html',
        'investigator_police_station_list',
        'Police Station',
        'Manage police station dropdown values for investigation reports.',
    )


@login_required
@investigator_admin_required
def police_station_edit(request, pk):
    return master_edit_view(
        request,
        pk,
        PoliceStation,
        PoliceStationForm,
        'investigator/master_edit.html',
        'investigator_police_station_list',
        'Police Station',
    )


@login_required
@investigator_admin_required
def police_station_toggle(request, pk):
    return master_toggle_view(request, pk, PoliceStation, 'investigator_police_station_list', 'Police Station')
