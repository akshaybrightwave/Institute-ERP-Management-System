from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Exam, StudentAnswer, StudentExamAttempt, StudentProfile, TeacherProfile
from .forms import ExamForm, StudentProfileForm, TeacherProfileForm
from accounts.views import admin_required  # import your decorator
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test,login_required
from django.utils.timezone import now
import csv

# Create your views here.

# helpers for role check
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'

def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'

def is_admin_or_teacher(user):
    return is_admin(user) or is_teacher(user)


@user_passes_test(is_admin_or_teacher)
def exam_list(request):
    if request.user.role == 'teacher':
        exams = Exam.objects.filter(created_by=request.user)
    else:
        exams = Exam.objects.all()

    query = request.GET.get('q', '').strip()
    if query:
        exams = exams.filter(title__icontains=query)

    return render(request, 'exam/exam_list.html', {'exams': exams, 'query': query})

@user_passes_test(is_admin_or_teacher)
def add_exam(request):
    if request.method == 'POST':
        form = ExamForm(request.POST)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            return redirect('exam_list')
    else:
        form = ExamForm()
    return render(request, 'exam/add_exam.html', {'form': form})



@user_passes_test(is_admin_or_teacher)
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # ✅ Teacher can edit only own exams
    if request.user.role == 'teacher' and exam.created_by != request.user:
        return redirect('exam_list')

    form = ExamForm(request.POST or None, instance=exam)
    if form.is_valid():
        form.save()
        return redirect('exam_list')
    return render(request, 'exam/edit_exam.html', {'form': form, 'exam': exam})



@user_passes_test(is_admin_or_teacher)
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # ✅ Teacher can delete only own exams
    if request.user.role == 'teacher' and exam.created_by != request.user:
        return redirect('exam_list')

    exam.delete()
    return redirect('exam_list')



# add question 
from .models import Exam, Question
from .forms import QuestionForm
from accounts.views import admin_required


# Exam question dashboard
@user_passes_test(is_admin_or_teacher)
def exam_question_dashboard_view(request):
    exams = Exam.objects.all()
    return render(request, 'exam/exam_question_dashboard.html', {'exams': exams})



@user_passes_test(is_teacher)
def teacher_exam_dashboard(request):
    exams = Exam.objects.filter(created_by=request.user)
    return render(request, 'exam/teacher_exam_dashboard.html', {'exams': exams})









@user_passes_test(is_admin_or_teacher)
def question_list(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Teacher can only view own exam's questions
    if request.user.role == 'teacher' and exam.created_by != request.user:
        return redirect('exam_list')

    questions = exam.questions.all()
    return render(request, 'exam/question_list.html', {'exam': exam, 'questions': questions})


# Make sure you import Option at the top!
from .models import Exam, Question, Option 

@user_passes_test(is_admin_or_teacher)
def add_question(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Security check
    if request.user.role == 'teacher' and exam.created_by != request.user:
        return redirect('exam_list')

    if request.method == 'POST':
        form = QuestionForm(request.POST)
        
        # Grab the dynamic options from our new HTML form
        option_texts = request.POST.getlist('option_text')
        correct_index = request.POST.get('is_correct') 

        if form.is_valid() and option_texts and correct_index is not None:
            # 1. Save the Question first
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            # 2. Loop through and save all the Options dynamically!
            correct_index = int(correct_index)
            for index, text in enumerate(option_texts):
                if text.strip(): # Ignore empty boxes
                    Option.objects.create(
                        question=question,
                        text=text.strip(),
                        is_correct=(index == correct_index)
                    )
            
            messages.success(request, "Question and options added successfully!")
            return redirect('question_list', exam_id=exam.id)
        else:
            messages.error(request, "Please fill out all fields and select the correct answer.")
    else:
        form = QuestionForm()
        
    return render(request, 'exam/add_question.html', {'form': form, 'exam': exam})

@user_passes_test(is_admin_or_teacher)
def edit_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.user.role == 'teacher' and question.exam.created_by != request.user:
        return redirect('exam_list')

    form = QuestionForm(request.POST or None, instance=question)
    if form.is_valid():
        form.save()
        return redirect('question_list', exam_id=question.exam.id)
    return render(request, 'exam/edit_question.html', {'form': form, 'exam': question.exam})


@user_passes_test(is_admin_or_teacher)
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.user.role == 'teacher' and question.exam.created_by != request.user:
        return redirect('exam_list')

    exam_id = question.exam.id
    question.delete()
    return redirect('question_list', exam_id=exam_id)

# student views


@login_required
def student_exam_list(request):
    exams = Exam.objects.filter(is_published=True)
    return render(request, 'student/student_exam_list.html', {'exams': exams})


@login_required
def attempt_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    attempts = StudentExamAttempt.objects.filter(student=request.user, exam=exam)
    in_progress_attempt = attempts.filter(is_completed=False).order_by('-start_time').first()
    completed_attempt = attempts.filter(is_completed=True).order_by('-submitted_at').first()

    # 🛡️ SECURITY CHECK 1: Has the student already completed this (and retakes aren't allowed)?
    if completed_attempt and not in_progress_attempt and not exam.allow_retake:
        messages.warning(request, "You have already completed this exam.")
        return redirect('student_exam_result', attempt_id=completed_attempt.id)

    # 🛡️ SECURITY CHECK 2: Is this exam past its deadline for new attempts?
    if exam.end_date and now() > exam.end_date and not in_progress_attempt:
        messages.error(request, "This exam is closed and no longer accepts new attempts.")
        return redirect('exam_instructions', exam_id=exam.id)

    # ⏱️ START THE CLOCK: If they haven't started (or are retaking), create the attempt NOW.
    attempt = in_progress_attempt or StudentExamAttempt.objects.create(student=request.user, exam=exam)

    questions = exam.questions.all().order_by('?')
    total_marks = sum(question.marks for question in questions)

    # Calculate exactly how many seconds they have left based on the SERVER time
    elapsed_time = (now() - attempt.start_time).total_seconds()
    remaining_seconds = max(0, (exam.duration_minutes * 60) - elapsed_time)

    # If they closed the tab and came back after time expired:
    if remaining_seconds <= 0:
        messages.error(request, "Your time for this exam has expired.")
        attempt.is_completed = True
        attempt.save()
        return redirect('student_exam_result', attempt_id=attempt.id)

    return render(request, 'exam/attempt_exam.html', {
        'exam': exam,
        'questions': questions,
        'total_marks': total_marks,
        'remaining_seconds': remaining_seconds,  # Send exact remaining time to HTML
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
            # Grab the ID of the Option the student selected
            selected_option_id = request.POST.get(str(question.id))

            if selected_option_id:
                try:
                    # Fetch the actual Option object from the database
                    selected_option = Option.objects.get(id=selected_option_id)

                    # Save their answer
                    StudentAnswer.objects.create(
                        attempt=attempt,
                        question=question,
                        selected_option=selected_option
                    )

                    # Award or deduct marks based on correctness
                    if selected_option.is_correct:
                        marks_earned += question.marks
                    else:
                        marks_earned -= exam.negative_marks

                except Option.DoesNotExist:
                    pass # Handle safely if data gets corrupted

        # Calculate final score (clamp negative totals to 0)
        marks_earned = max(0, marks_earned)
        score = (marks_earned / total_marks) * 100 if total_marks > 0 else 0
        attempt.score = score
        attempt.is_completed = True
        attempt.save()

        messages.success(request, "Exam submitted successfully!")
        return redirect('student_exam_result', attempt_id=attempt.id)
    else:
        return redirect('student_exam_list')

#update
@login_required
def student_exam_result(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id, student=request.user)
    answers = attempt.answers.all()

    # Calculate total marks possible for the exam
    total_marks = sum(question.marks for question in attempt.exam.questions.all())

    # Calculate marks earned, accounting for negative marking on wrong answers
    marks_earned = 0
    for ans in answers:
        if ans.selected_option:
            if ans.selected_option.is_correct:
                marks_earned += ans.question.marks
            else:
                marks_earned -= attempt.exam.negative_marks
    marks_earned = max(0, marks_earned)

    # Calculate percentage score
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
    
    # Optional: Render confirmation page if you want
    return render(request, 'student/confirm_delete_attempt.html', {'attempt': attempt})



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



# student dashboard
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

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


@login_required
def exam_instructions_view(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Get latest attempt of this student for this exam (if exists)
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




#teacher dashboard
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count, Avg, Q, F
from .models import Exam, TeacherProfile


@login_required
def teacher_dashboard(request):
    if request.user.role != 'teacher':
        return redirect('login')

    profile, created = TeacherProfile.objects.get_or_create(user=request.user)

    if created:
        # If profile was just created, redirect them to edit the profile first
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

    context = {
        'profile': profile,
        'exams': exams,
        'total_exams': total_exams,
        'total_submissions': total_submissions,
        'total_questions': total_questions
    }
    return render(request, 'teacher/teacher_dashboard.html', context)





def teacher_profile(request):
    if request.user.role != 'teacher':
        return redirect('login')

    # Try to get or create the profile
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
    return render(request, 'teacher/teacher_profile_detail.html', {'profile': profile})


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


from django.contrib.auth import logout

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


#submission
from django.db.models import Q
from datetime import datetime

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

    # Aggregate stats for the (filtered) submissions
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
        'answers': answers
    })































