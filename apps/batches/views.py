from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count
from apps.accounts.views import admin_required
from .models import Batch
from .forms import BatchForm


@admin_required
def batch_list(request):
    batches = Batch.objects.all().select_related('course', 'teacher').annotate(student_count=Count('studentprofile'))
    return render(request, 'batches/batch_list.html', {'batches': batches})


@admin_required
def batch_detail(request, pk):
    batch = get_object_or_404(Batch.objects.select_related('course', 'teacher'), pk=pk)
    students = batch.studentprofile_set.all()
    exams = batch.exams.all()
    
    from django.db.models import Q, Count
    attendance_history = batch.attendances.values('date').annotate(
        present_count=Count('id', filter=Q(status='present')),
        absent_count=Count('id', filter=Q(status='absent'))
    ).order_by('-date')
    
    return render(request, 'batches/batch_detail.html', {
        'batch': batch,
        'students': students,
        'exams': exams,
        'attendance_history': attendance_history
    })


@admin_required
def batch_create(request):
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch created successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm()
    return render(request, 'batches/batch_form.html', {'form': form, 'action': 'Create'})


@admin_required
def batch_update(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        form = BatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch updated successfully.')
            return redirect('batch_list')
    else:
        form = BatchForm(instance=batch)
    return render(request, 'batches/batch_form.html', {'form': form, 'action': 'Update', 'batch': batch})


@admin_required
def batch_delete(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    if request.method == 'POST':
        batch.delete()
        messages.success(request, 'Batch deleted successfully.')
        return redirect('batch_list')
    return render(request, 'batches/batch_confirm_delete.html', {'batch': batch})
