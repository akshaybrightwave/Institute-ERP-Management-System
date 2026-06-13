from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q, F
from datetime import datetime
import csv

from apps.exams.models import Exam, StudentExamAttempt
from apps.teachers.models import TeacherProfile
from apps.teachers.forms import TeacherProfileForm


# ---------------------------------------------------------------------------
# Teacher Dashboard
# ---------------------------------------------------------------------------

@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile, created = TeacherProfile.objects.get_or_create(user=request.user)

    if created:
        messages.info(request, 'Please complete your profile before accessing the dashboard.')
        return redirect('edit_teacher_profile')

    exams_qs = Exam.objects.filter(created_by=request.user).annotate(
        submission_count=Count('attempts', distinct=True),
        question_count=Count('questions', distinct=True),
        completed_count=Count('attempts', filter=Q(attempts__is_completed=True), distinct=True),
        avg_score=Avg('attempts__score', filter=Q(attempts__is_completed=True)),
        pass_count=Count(
            'attempts',
            filter=Q(attempts__is_completed=True, attempts__score__gte=F('pass_percentage')),
            distinct=True,
        ),
    )

    total_exams = exams_qs.count()
    total_submissions = sum(exam.submission_count for exam in exams_qs)
    total_questions = sum(exam.question_count for exam in exams_qs)

    paginator = Paginator(exams_qs, 5)
    exams = paginator.get_page(request.GET.get('page'))

    for exam in exams:
        exam.pass_rate = round((exam.pass_count / exam.completed_count) * 100, 1) if exam.completed_count else None

    # Teacher Batches and Students metrics
    from apps.batches.models import Batch
    assigned_batches = Batch.objects.filter(teacher=profile).select_related('course').annotate(student_count=Count('studentprofile'))
    total_assigned_batches = assigned_batches.count()
    total_students_across_batches = assigned_batches.aggregate(total=Count('studentprofile'))['total'] or 0

    context = {
        'profile': profile,
        'exams': exams,
        'total_exams': total_exams,
        'total_submissions': total_submissions,
        'total_questions': total_questions,
        'assigned_batches': assigned_batches,
        'total_assigned_batches': total_assigned_batches,
        'total_students_across_batches': total_students_across_batches,
    }
    return render(request, 'teacher/teacher_dashboard.html', context)


@login_required
def teacher_batch_detail(request, pk):
    if request.user.role != 'teacher':
        return redirect('login')

    profile = get_object_or_404(TeacherProfile, user=request.user)
    from apps.batches.models import Batch
    # SECURITY: Validate ownership
    batch = get_object_or_404(Batch.objects.select_related('course', 'teacher'), pk=pk, teacher=profile)
    students = batch.studentprofile_set.all()

    return render(request, 'teacher/batch_detail.html', {
        'batch': batch,
        'students': students,
    })


# ---------------------------------------------------------------------------
# Teacher Profile
# ---------------------------------------------------------------------------

@login_required
def teacher_profile(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile, created = TeacherProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = TeacherProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('teacher_profile')
    else:
        form = TeacherProfileForm(instance=profile)

    return render(request, 'teacher/teacher_profile.html', {'form': form})


@login_required
def teacher_profile_detail(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile = get_object_or_404(TeacherProfile, user=request.user)
    from apps.batches.models import Batch
    assigned_batches = Batch.objects.filter(teacher=profile).select_related('course')
    assigned_count = assigned_batches.count()

    return render(request, 'teacher/teacher_profile_detail.html', {
        'profile': profile,
        'assigned_batches': assigned_batches,
        'assigned_count': assigned_count,
    })


@login_required
def edit_teacher_profile(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile, created = TeacherProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = TeacherProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('teacher_dashboard')
    else:
        form = TeacherProfileForm(instance=profile)

    return render(request, 'teacher/edit_profile.html', {'form': form})


@login_required
def delete_teacher_profile(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile = get_object_or_404(TeacherProfile, user=request.user)

    if request.method == 'POST':
        user = request.user
        profile.delete()
        user.delete()
        logout(request)
        messages.success(request, 'Your profile and account have been deleted.')
        return redirect('home')
    return render(request, 'teacher/confirm_delete.html')


# ---------------------------------------------------------------------------
# Submissions & Student Answers
# ---------------------------------------------------------------------------

@login_required
def teacher_exam_dashboard(request):
    exams = Exam.objects.filter(created_by=request.user)
    return render(request, 'exam/teacher_exam_dashboard.html', {'exams': exams})


@login_required
def view_submissions(request, exam_id):
    if request.user.role != 'teacher':
        return redirect('login')

    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    attempts = StudentExamAttempt.objects.filter(exam=exam)

    # Filtering
    score_min = request.GET.get('score_min')
    date_from = request.GET.get('date_from')

    if score_min:
        attempts = attempts.filter(score__gte=score_min)
    if date_from:
        attempts = attempts.filter(submitted_at__date__gte=date_from)

    scores = [a.score for a in attempts]
    total_attempts = len(scores)
    average_score = round(sum(scores) / total_attempts, 1) if total_attempts else 0
    highest_score = round(max(scores), 1) if total_attempts else 0
    lowest_score = round(min(scores), 1) if total_attempts else 0
    pass_count = sum(1 for s in scores if s >= exam.pass_percentage)
    pass_rate = round((pass_count / total_attempts) * 100, 1) if total_attempts else 0

    return render(request, 'teacher/view_submissions.html', {
        'exam': exam,
        'attempts': attempts,
        'score_min': score_min,
        'date_from': date_from,
        'total_attempts': total_attempts,
        'average_score': average_score,
        'highest_score': highest_score,
        'lowest_score': lowest_score,
        'pass_rate': pass_rate,
    })


@login_required
def export_submissions_csv(request, exam_id):
    if request.user.role != 'teacher':
        return redirect('login')

    exam = get_object_or_404(Exam, id=exam_id, created_by=request.user)
    attempts = StudentExamAttempt.objects.filter(exam=exam)

    score_min = request.GET.get('score_min')
    date_from = request.GET.get('date_from')

    if score_min:
        attempts = attempts.filter(score__gte=score_min)
    if date_from:
        attempts = attempts.filter(submitted_at__date__gte=date_from)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{exam.title}_submissions.csv"'

    writer = csv.writer(response)
    writer.writerow(['Student', 'Score (%)', 'Result', 'Submitted On'])
    for attempt in attempts.order_by('-submitted_at'):
        result = 'Pass' if attempt.score >= exam.pass_percentage else 'Fail'
        writer.writerow([
            attempt.student.username,
            attempt.score,
            result,
            attempt.submitted_at.strftime('%Y-%m-%d %H:%M'),
        ])

    return response


@login_required
def view_student_answers(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id)
    if request.user.role != 'teacher' or attempt.exam.created_by != request.user:
        return redirect('login')

    answers = attempt.answers.select_related('question')
    return render(request, 'teacher/view_student_answers.html', {
        'attempt': attempt,
        'answers': answers,
    })
