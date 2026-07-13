from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST

from .models import Category
from .forms import CategoryForm


def _check_permission(request):
    """Allow admin and superadmin only."""
    return request.user.role in ('admin', 'superadmin')


@login_required
def category_list(request):
    if not _check_permission(request):
        return HttpResponseForbidden('Access Denied: Unauthorized role.')

    form = CategoryForm()

    # Handle create (POST to the same page)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category published successfully.')
            return redirect('category_list')
        # Form is invalid — fall through to render with errors

    # Listing with search + pagination
    query = request.GET.get('q', '').strip()
    qs = Category.objects.all().order_by('-created_at', '-id')
    if query:
        qs = qs.filter(name__icontains=query)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'categories/category_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@login_required
def category_edit(request, pk):
    """AJAX-friendly: returns JSON for modal, processes update."""
    if not _check_permission(request):
        return HttpResponseForbidden('Access Denied: Unauthorized role.')

    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('category_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
            # Non-AJAX fallback: re-render the list with modal errors preserved
            query = request.GET.get('q', '').strip()
            qs = Category.objects.all().order_by('-created_at', '-id')
            if query:
                qs = qs.filter(name__icontains=query)
            paginator = Paginator(qs, 10)
            page_obj = paginator.get_page(request.GET.get('page', 1))
            return render(request, 'categories/category_list.html', {
                'form': CategoryForm(),
                'edit_form': form,
                'edit_category': category,
                'page_obj': page_obj,
                'query': query,
            })

    # GET: return category data as JSON for the modal
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'id': category.pk, 'name': category.name})

    return redirect('category_list')


@login_required
def category_delete(request, pk):
    if not _check_permission(request):
        return HttpResponseForbidden('Access Denied: Unauthorized role.')

    category = get_object_or_404(Category, pk=pk)

    if request.method == 'POST':
        name = category.name
        category.delete()   # Soft delete via SoftDeleteModel
        messages.success(request, f'Category "{name}" deleted successfully.')
        return redirect('category_list')

    return render(request, 'categories/category_confirm_delete.html', {
        'category': category,
    })
