from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from .models import TimeTable, AcademicSession, Occupation
from .forms import TimeTableForm, AcademicSessionForm, OccupationForm


def _check_permission(request):
    if request.user.role not in ('admin', 'center', 'superadmin'):
        return False
    return True


# ────────────────────────────────────────────────────────
# Time Table Views
# ────────────────────────────────────────────────────────

@login_required
def timetable_list(request):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    form = TimeTableForm()

    if request.method == 'POST':
        form = TimeTableForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Time Table published successfully.')
            return redirect('timetable_list')

    query = request.GET.get('q', '').strip()
    qs = TimeTable.objects.all().order_by('-id')
    if query:
        qs = qs.filter(timetable_name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'academics/timetable/timetable_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def timetable_edit(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    timetable = get_object_or_404(TimeTable, pk=pk)

    if request.method == 'POST':
        form = TimeTableForm(request.POST, instance=timetable)
        if form.is_valid():
            form.save()
            messages.success(request, f'Time Table "{timetable.timetable_name}" updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('timetable_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'id': timetable.pk, 'name': timetable.timetable_name})

    return redirect('timetable_list')


@login_required
def timetable_delete(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    timetable = get_object_or_404(TimeTable, pk=pk)

    if request.method == 'POST':
        name = timetable.timetable_name
        timetable.delete()
        messages.success(request, f'Time Table "{name}" deleted successfully.')
        return redirect('timetable_list')

    return render(request, 'academics/timetable/timetable_confirm_delete.html', {
        'timetable': timetable,
    })


# ────────────────────────────────────────────────────────
# Academic Session Views
# ────────────────────────────────────────────────────────

@login_required
def session_list(request):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    form = AcademicSessionForm()

    if request.method == 'POST':
        form = AcademicSessionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Session published successfully.')
            return redirect('session_list')

    query = request.GET.get('q', '').strip()
    qs = AcademicSession.objects.all().order_by('-id')
    if query:
        qs = qs.filter(session_name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'academics/session/session_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def session_edit(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    session_obj = get_object_or_404(AcademicSession, pk=pk)

    if request.method == 'POST':
        form = AcademicSessionForm(request.POST, instance=session_obj)
        if form.is_valid():
            form.save()
            messages.success(request, f'Session "{session_obj.session_name}" updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('session_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'id': session_obj.pk, 'name': session_obj.session_name})

    return redirect('session_list')


@login_required
def session_delete(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    session_obj = get_object_or_404(AcademicSession, pk=pk)

    if request.method == 'POST':
        name = session_obj.session_name
        session_obj.delete()
        messages.success(request, f'Session "{name}" deleted successfully.')
        return redirect('session_list')

    return render(request, 'academics/session/session_confirm_delete.html', {
        'session': session_obj,
    })


@login_required
def session_toggle_status(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    session_obj = get_object_or_404(AcademicSession, pk=pk)
    if request.method == 'POST':
        session_obj.status = not session_obj.status
        session_obj.save()
        return JsonResponse({'success': True, 'status': session_obj.status})

    return JsonResponse({'success': False}, status=400)


# ────────────────────────────────────────────────────────
# Occupation Views
# ────────────────────────────────────────────────────────

@login_required
def occupation_list(request):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    form = OccupationForm()

    if request.method == 'POST':
        form = OccupationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Occupation published successfully.')
            return redirect('occupation_list')

    query = request.GET.get('q', '').strip()
    qs = Occupation.objects.all().order_by('-id')
    if query:
        qs = qs.filter(occupation_name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'academics/occupation/occupation_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def occupation_edit(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    occupation = get_object_or_404(Occupation, pk=pk)

    if request.method == 'POST':
        form = OccupationForm(request.POST, instance=occupation)
        if form.is_valid():
            form.save()
            messages.success(request, f'Occupation "{occupation.occupation_name}" updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('occupation_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'id': occupation.pk, 'name': occupation.occupation_name})

    return redirect('occupation_list')


@login_required
def occupation_delete(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    occupation = get_object_or_404(Occupation, pk=pk)

    if request.method == 'POST':
        name = occupation.occupation_name
        occupation.delete()
        messages.success(request, f'Occupation "{name}" deleted successfully.')
        return redirect('occupation_list')

    return render(request, 'academics/occupation/occupation_confirm_delete.html', {
        'occupation': occupation,
    })
