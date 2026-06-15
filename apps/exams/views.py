from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from .models import Exam, Question, Option, StudentAnswer, StudentExamAttempt
from .forms import ExamForm, QuestionForm, OptionForm
from apps.accounts.views import admin_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.timezone import now


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'


def is_admin_or_teacher(user):
    return is_admin(user) or is_teacher(user)


# ---------------------------------------------------------------------------
# Exam CRUD  (Admin + Teacher)
# ---------------------------------------------------------------------------

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
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save(commit=False)
            exam.created_by = request.user
            exam.save()
            form.save_m2m()
            return redirect('exam_list')
    else:
        form = ExamForm(user=request.user)
    return render(request, 'exam/add_exam.html', {'form': form})


@user_passes_test(is_admin_or_teacher)
def edit_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Teacher can edit only exams connected to their assigned batches
    if request.user.role == 'teacher' and not exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    form = ExamForm(request.POST or None, instance=exam, user=request.user)
    if form.is_valid():
        form.save()
        return redirect('exam_list')
    return render(request, 'exam/edit_exam.html', {'form': form, 'exam': exam})


@user_passes_test(is_admin_or_teacher)
def delete_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Teacher can delete only exams connected to their assigned batches
    if request.user.role == 'teacher' and not exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    exam.delete()
    return redirect('exam_list')


# ---------------------------------------------------------------------------
# Question CRUD  (Admin + Teacher)
# ---------------------------------------------------------------------------

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

    # Teacher can only view questions for exams connected to their assigned batches
    if request.user.role == 'teacher' and not exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    questions = exam.questions.all()
    return render(request, 'exam/question_list.html', {'exam': exam, 'questions': questions})


@user_passes_test(is_admin_or_teacher)
def add_question(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Security check: Teacher can only add questions to exams connected to their assigned batches
    if request.user.role == 'teacher' and not exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    if request.method == 'POST':
        form = QuestionForm(request.POST)

        # Grab the dynamic options from the HTML form
        option_texts = request.POST.getlist('option_text')
        correct_index = request.POST.get('is_correct')

        if form.is_valid() and option_texts and correct_index is not None:
            # 1. Save the Question first
            question = form.save(commit=False)
            question.exam = exam
            question.save()

            # 2. Loop through and save all the Options dynamically
            correct_index = int(correct_index)
            for index, text in enumerate(option_texts):
                if text.strip():  # Ignore empty boxes
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

    if request.user.role == 'teacher' and not question.exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    form = QuestionForm(request.POST or None, instance=question)
    if form.is_valid():
        form.save()
        messages.success(request, "Question updated successfully!")
        return redirect('question_list', exam_id=question.exam.id)
        
    options = question.options.all()
    return render(request, 'exam/edit_question.html', {
        'form': form, 
        'exam': question.exam, 
        'question': question, 
        'options': options
    })


@user_passes_test(is_admin_or_teacher)
def delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.user.role == 'teacher' and not question.exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    exam_id = question.exam.id
    question.delete()
    return redirect('question_list', exam_id=exam_id)


# ---------------------------------------------------------------------------
# Option CRUD  (Admin + Teacher)
# ---------------------------------------------------------------------------

@user_passes_test(is_admin_or_teacher)
def add_option(request, question_id):
    question = get_object_or_404(Question, id=question_id)

    if request.user.role == 'teacher' and not question.exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    if request.method == 'POST':
        form = OptionForm(request.POST)
        if form.is_valid():
            option = form.save(commit=False)
            option.question = question
            option.save()
            messages.success(request, "Option added successfully!")
            return redirect('edit_question', question_id=question.id)
    else:
        form = OptionForm()

    return render(request, 'exam/option_form.html', {
        'form': form,
        'question': question,
        'action': 'Add Option'
    })


@user_passes_test(is_admin_or_teacher)
def edit_option(request, option_id):
    option = get_object_or_404(Option, id=option_id)
    question = option.question

    if request.user.role == 'teacher' and not question.exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    form = OptionForm(request.POST or None, instance=option)
    if form.is_valid():
        form.save()
        messages.success(request, "Option updated successfully!")
        return redirect('edit_question', question_id=question.id)

    return render(request, 'exam/option_form.html', {
        'form': form,
        'question': question,
        'action': 'Edit Option'
    })


@user_passes_test(is_admin_or_teacher)
def delete_option(request, option_id):
    option = get_object_or_404(Option, id=option_id)
    question = option.question

    if request.user.role == 'teacher' and not question.exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    option.delete()
    messages.success(request, "Option deleted successfully!")
    return redirect('edit_question', question_id=question.id)


@user_passes_test(is_admin_or_teacher)
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    # Validate ownership for teachers
    if request.user.role == 'teacher':
        from apps.teachers.models import TeacherProfile
        profile = TeacherProfile.objects.filter(user=request.user).first()
        if not profile or not exam.batches.filter(teacher=profile).exists():
            return redirect('exam_list')

    # Assigned Batches
    batches = exam.batches.all()

    # Student Count: count of unique students in all batches assigned to this exam
    from apps.students.models import StudentProfile
    student_count = StudentProfile.objects.filter(batch__in=batches).count()

    # Attempt Count: count of all attempts on this exam
    attempt_count = exam.attempts.count()

    return render(request, 'exam/exam_detail.html', {
        'exam': exam,
        'batches': batches,
        'student_count': student_count,
        'attempt_count': attempt_count,
    })

    # NOTE: All student views  → apps/students/views.py
    #       All teacher views  → apps/teachers/views.py
