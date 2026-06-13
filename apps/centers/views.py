from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.accounts.views import admin_required
from .models import Center
from .forms import CenterForm


@admin_required
def center_list(request):
    centers = Center.objects.all()
    return render(request, 'centers/center_list.html', {'centers': centers})


@admin_required
def center_create(request):
    if request.method == 'POST':
        form = CenterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Center created successfully.')
            return redirect('center_list')
    else:
        form = CenterForm()
    return render(request, 'centers/center_form.html', {'form': form, 'action': 'Create'})


@admin_required
def center_update(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        form = CenterForm(request.POST, instance=center)
        if form.is_valid():
            form.save()
            messages.success(request, 'Center updated successfully.')
            return redirect('center_list')
    else:
        form = CenterForm(instance=center)
    return render(request, 'centers/center_form.html', {'form': form, 'action': 'Update', 'center': center})


@admin_required
def center_delete(request, pk):
    center = get_object_or_404(Center, pk=pk)
    if request.method == 'POST':
        center.delete()
        messages.success(request, 'Center deleted successfully.')
        return redirect('center_list')
    return render(request, 'centers/center_confirm_delete.html', {'center': center})
