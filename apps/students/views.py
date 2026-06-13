from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now

from apps.exams.models import Exam, StudentExamAttempt, StudentAnswer, Option
from apps.students.models import StudentProfile
from apps.students.forms import StudentProfileForm


# ---------------------------------------------------------------------------
# Student Dashboard
# ---------------------------------------------------------------------------

@login_required
def student_dashboard(request):
    if request.user.role != 'student':
        return redirect('login')

    attempts = StudentExamAttempt.objects.filter(student=request.user)
    total_attempts = attempts.count()
    average_score = sum(a.score for a in attempts) / total_attempts if total_attempts > 0 else 0

    context = {
        'total_exams': Exam.objects.filter(is_published=True).count(),
        'total_attempts': total_attempts,
        'average_score': round(average_score, 1),
    }
    return render(request, 'student/student_dashboard.html', context)


# ---------------------------------------------------------------------------
# Exam browsing & instructions
# ---------------------------------------------------------------------------

@login_required
def student_exam_list(request):
    exams = Exam.objects.filter(is_published=True)
    return render(request, 'student/student_exam_list.html', {'exams': exams})


@login_required
def exam_instructions_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    attempts = StudentExamAttempt.objects.filter(student=request.user, exam=exam)
    latest_attempt = attempts.order_by('-submitted_at').first()
    in_progress_attempt = attempts.filter(is_completed=False).first()
    completed_attempt = attempts.filter(is_completed=True).order_by('-submitted_at').first()

    is_closed = exam.end_date and now() > exam.end_date and not in_progress_attempt
    can_start = not is_closed and (not completed_attempt or exam.allow_retake or in_progress_attempt)

    return render(request, 'student/exam_instructions.html', {
        'exam': exam,
        'latest_attempt': latest_attempt,
        'is_closed': is_closed,
        'can_start': can_start,
    })


# ---------------------------------------------------------------------------
# Exam attempt & submit
# ---------------------------------------------------------------------------

@login_required
def attempt_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    attempts = StudentExamAttempt.objects.filter(student=request.user, exam=exam)
    in_progress_attempt = attempts.filter(is_completed=False).order_by('-start_time').first()
    completed_attempt = attempts.filter(is_completed=True).order_by('-submitted_at').first()

    # SECURITY CHECK 1: Already completed and retakes not allowed
    if completed_attempt and not in_progress_attempt and not exam.allow_retake:
        messages.warning(request, "You have already completed this exam.")
        return redirect('student_exam_result', attempt_id=completed_attempt.id)

    # SECURITY CHECK 2: Past deadline for new attempts
    if exam.end_date and now() > exam.end_date and not in_progress_attempt:
        messages.error(request, "This exam is closed and no longer accepts new attempts.")
        return redirect('exam_instructions', exam_id=exam.id)

    # Start the clock: create attempt if needed
    attempt = in_progress_attempt or StudentExamAttempt.objects.create(student=request.user, exam=exam)

    questions = exam.questions.all().order_by('?')
    total_marks = sum(question.marks for question in questions)

    # Calculate remaining seconds from server time
    elapsed_time = (now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, (exam.duration_minutes * 60) - elapsed_time)

    # Time expired while tab was closed
    if remaining_seconds <= 0:
        messages.error(request, "Your time for this exam has expired.")
        attempt.is_completed = True
        attempt.save()
        return redirect('student_exam_result', attempt_id=attempt.id)

    return render(request, 'exam/attempt_exam.html', {
        'exam': exam,
        'questions': questions,
        'total_marks': total_marks,
        'remaining_seconds': remaining_seconds,
    })


@login_required
def submit_exam(request, exam_id):
    if request.method == 'POST':
        exam = get_object_or_404(Exam, id=exam_id)
        student = request.user
        attempt = StudentExamAttempt.objects.filter(
            student=student, exam=exam, is_completed=False
        ).order_by('-start_time').first()

        if not attempt:
            messages.warning(request, "No active exam attempt found.")
            return redirect('student_exam_list')

        # Time validation check
        elapsed_time = (now() - attempt.start_time).total_seconds()
        allowed_time = (exam.duration_minutes * 60) + 60

        if elapsed_time > allowed_time:
            messages.error(request, "Time expired! Your submission was rejected.")
            attempt.is_completed = True
            attempt.save()
            return redirect('student_exam_result', attempt_id=attempt.id)

        # --- GRADING LOGIC (marks-weighted, with negative marking) ---
        total_marks = sum(question.marks for question in exam.questions.all())
        marks_earned = 0

        for question in exam.questions.all():
            selected_option_id = request.POST.get(str(question.id))

            if selected_option_id:
                try:
                    selected_option = Option.objects.get(id=selected_option_id)
                    StudentAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_option
                    )
                    if selected_option.is_correct:
                        marks_earned += question.marks
                    else:
                        marks_earned -= exam.negative_marks
                except Option.DoesNotExist:
                    pass

        marks_earned = max(0, marks_earned)
        score = (marks_earned / total_marks) * 100 if total_marks > 0 else 0
        attempt.score = score
        attempt.is_completed = True
        attempt.save()

        messages.success(request, "Exam submitted successfully!")
        return redirect('student_exam_result', attempt_id=attempt.id)
    else:
        return redirect('student_exam_list')


# ---------------------------------------------------------------------------
# Results & History
# ---------------------------------------------------------------------------

@login_required
def student_exam_result(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)
    answers = attempt.answers.all()

    total_marks = sum(question.marks for question in attempt.exam.questions.all())

    marks_earned = 0
    for ans in answers:
        if ans.selected_option:
            if ans.selected_option.is_correct:
                marks_earned += ans.question.marks
            else:
                marks_earned -= attempt.exam.negative_marks
    marks_earned = max(0, marks_earned)

    rounded_score = int(round(attempt.score))
    progress_width = f"width: {rounded_score}%;"
    passed = attempt.score >= attempt.exam.pass_percentage

    return render(request, 'student/student_exam_result.html', {
        'attempt': attempt,
        'answers': answers,
        'total_marks': total_marks,
        'marks_earned': marks_earned,
        'rounded_score': rounded_score,
        'progress_width': progress_width,
        'passed': passed,
    })


@login_required
def student_exam_history(request):
    attempts = StudentExamAttempt.objects.filter(student=request.user).order_by('-submitted_at')
    return render(request, 'student/student_exam_history.html', {'attempts': attempts})


@login_required
def delete_student_exam_attempt(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)

    if request.method == 'POST':
        attempt.delete()
        messages.success(request, "Exam attempt deleted successfully.")
        return redirect('student_exam_history')

    return render(request, 'student/confirm_delete_attempt.html', {'attempt': attempt})


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------

@login_required
def student_profile(request):
    student = request.user
    attempts = StudentExamAttempt.objects.filter(student=student)
    total_attempts = attempts.count()

    if total_attempts > 0:
        average_score = sum(a.score for a in attempts) / total_attempts
    else:
        average_score = 0

    return render(request, 'student/student_profile.html', {
        'student': student,
        'attempts': attempts,
        'total_attempts': total_attempts,
        'average_score': round(average_score, 2),
    })


@login_required
def edit_student_profile(request):
    profile, created = StudentProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = StudentProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('student_profile')
    else:
        form = StudentProfileForm(instance=profile)

    return render(request, 'student/edit_profile.html', {'form': form})
