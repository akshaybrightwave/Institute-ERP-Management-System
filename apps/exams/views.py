from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from .models import Exam, Question, Option, StudentAnswer, StudentExamAttempt, ExamSchedule, ExamScheduleSubject, ExamStudentAssignment, ExamCenterAssignment, ExamCentre
from .forms import ExamForm, QuestionForm, OptionForm, ExamScheduleForm
from apps.accounts.views import admin_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.timezone import now
from django.db.models import Avg, Max, Min, Q, Count, F
from django.db import transaction
from django.core.paginator import Paginator
from apps.centers.models import Center, CenterCourseAssignment
from apps.courses.models import Course
from apps.academics.models import AcademicSession
from apps.students.models import StudentProfile, StudentAdmission
from apps.batches.models import Batch
from apps.subjects.models import Subject, SubjectOrder
import csv
import io


# ---------------------------------------------------------------------------
# Role helpers
# ---------------------------------------------------------------------------

def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'


def is_admin_or_teacher(user):
    return is_admin(user) or is_teacher(user)


def is_admin_center_or_teacher(user):
    return user.is_authenticated and user.role in ['admin', 'center', 'teacher']


# ---------------------------------------------------------------------------
# Exam CRUD  (Admin + Teacher)
# ---------------------------------------------------------------------------

@user_passes_test(is_admin_center_or_teacher)
def exam_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    
    if is_center:
        # Retrieve all (active and soft-deleted) requests to show Pending and Approved states
        exams = Exam.all_objects.filter(center=request.user.center).select_related('course')
    elif is_teacher:
        exams = Exam.objects.filter(created_by=request.user).select_related('course', 'center')
    else:
        exams = Exam.objects.all().select_related('course', 'center')

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        exams = exams.filter(
            Q(title__icontains=q) |
            Q(course__name__icontains=q) |
            Q(course_duration__icontains=q)
        )

    # Order by newest first
    exams = exams.order_by('-id')

    # Export to CSV
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exams.csv"'
        writer = csv.writer(response)
        if is_center:
            writer.writerow(['Request ID', 'Course', 'Message', 'Created Date', 'Current Status'])
            for exam in exams:
                status_str = 'Approved' if exam.is_published else 'Pending'
                created_str = exam.start_datetime.strftime('%Y-%m-%d %H:%M') if exam.start_datetime else 'No Date'
                writer.writerow([
                    f"REQ-{exam.id}",
                    exam.course.name if exam.course else 'No Course',
                    exam.description,
                    created_str,
                    status_str
                ])
        else:
            writer.writerow(['Exam Title', 'Course', 'Course Duration', 'Start Date & Time', 'End Date & Time', 'Exam Timer', 'Status'])
            for exam in exams:
                start_str = exam.start_datetime.strftime('%Y-%m-%d %H:%M') if exam.start_datetime else 'No Schedule'
                end_str = exam.end_datetime.strftime('%Y-%m-%d %H:%M') if exam.end_datetime else 'No Schedule'
                timer_str = f"{exam.duration_minutes} Minutes" if exam.duration_minutes else 'No Timer'
                status_str = 'Active' if exam.is_published else 'Inactive'
                writer.writerow([
                    exam.title,
                    exam.course.name if exam.course else 'No Course',
                    exam.course_duration or '',
                    start_str,
                    end_str,
                    timer_str,
                    status_str
                ])
        return response

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        limit = int(show_entries)
    except ValueError:
        limit = 10

    paginator = Paginator(exams, limit)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'exam/exam_list.html', {
        'page_obj': page_obj,
        'query': q,
        'show_entries': show_entries,
        'is_center': is_center,
        'is_admin': is_admin,
        'is_teacher': is_teacher,
    })


TIMER_CHOICES = [10, 15, 20, 30, 45, 60, 90, 120, 150, 180]


@user_passes_test(is_admin_center_or_teacher)
def add_exam(request):
    is_center_role = request.user.role == 'center'
    if request.method == 'POST':
        form = ExamForm(request.POST, user=request.user)
        if form.is_valid():
            exam = form.save(commit=False)
            if is_center_role:
                exam.center = request.user.center
                exam.title = form.cleaned_data.get('title')
                exam.is_published = False
                exam.start_datetime = now()
                exam.date = now().date()
            else:
                # Populate date field for backwards compatibility
                if exam.start_datetime:
                    exam.date = exam.start_datetime.date()
                # If is_published comes as hidden "1", set it
                if request.POST.get('is_published') == '1':
                    exam.is_published = True
            
            exam.created_by = request.user
            exam.save()
            form.save_m2m()
            if is_center_role:
                messages.success(request, "Exam request submitted successfully!")
            else:
                messages.success(request, "Exam created successfully!")
            return redirect('exam_list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ExamForm(user=request.user)
    return render(request, 'exam/add_exam.html', {
        'form': form,
        'is_center': is_center_role,
        'timer_choices': TIMER_CHOICES,
    })


@login_required
def ajax_get_course_durations(request):
    course_id = request.GET.get('course_id')
    if not course_id:
        return JsonResponse({'choices': []})
    try:
        course = Course.objects.get(id=course_id)
        from apps.results.forms import ResultForm
        temp_form = ResultForm()
        choices = temp_form._parse_duration_choices(course.duration)
        return JsonResponse({'choices': choices})
    except Course.DoesNotExist:
        return JsonResponse({'choices': []})


@user_passes_test(is_admin_center_or_teacher)
def edit_exam(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'

    exam = get_object_or_404(Exam, id=exam_id)

    if is_center:
        if exam.center != request.user.center:
            return HttpResponseForbidden("Access Denied: You do not manage this center's exams.")
        if exam.is_published:
            messages.error(request, "Approved requests cannot be edited.")
            return redirect('exam_list')

    if is_teacher:
        if exam.created_by != request.user:
            return HttpResponseForbidden("Access Denied: You did not create this exam.")

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam, user=request.user)
        if form.is_valid():
            exam_obj = form.save(commit=False)
            if is_center:
                exam_obj.title = form.cleaned_data.get('title')
                exam_obj.is_published = False
                exam_obj.start_datetime = now()
                exam_obj.date = now().date()
            else:
                if exam_obj.start_datetime:
                    exam_obj.date = exam_obj.start_datetime.date()
            exam_obj.save()
            form.save_m2m()
            messages.success(request, "Exam updated successfully!")
            return redirect('exam_list')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ExamForm(instance=exam, user=request.user)
    return render(request, 'exam/edit_exam.html', {'form': form, 'exam': exam, 'is_center': is_center})


@login_required
def delete_exam(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")

    exam = get_object_or_404(Exam, id=exam_id)

    if is_center:
        if exam.center != request.user.center:
            return HttpResponseForbidden("Access Denied: You do not manage this center's exams.")
        if exam.is_published:
            messages.error(request, "Approved requests cannot be deleted.")
            return redirect('exam_list')

    exam.delete()
    messages.success(request, "Exam deleted successfully!")
    return redirect('exam_list')


@login_required
def ajax_toggle_exam_status(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    if not (is_admin or is_center):
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)
    
    if is_center:
        return JsonResponse({'success': False, 'message': 'Access Denied: Centers cannot change request status.'}, status=403)
    
    exam = get_object_or_404(Exam, id=exam_id)
    if is_center and exam.center != request.user.center:
        return JsonResponse({'success': False, 'message': 'Access Denied: You do not manage this exam.'}, status=403)
        
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body)
            status_val = data.get('status') # 'Active' or 'Inactive'
            exam.is_published = (status_val == 'Active')
            exam.save()
            return JsonResponse({'success': True, 'is_published': exam.is_published})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)


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

    questions = exam.questions.prefetch_related('options').all()
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


def _get_csv_value(row, *names):
    normalized = {str(k).strip().lower().replace(' ', '_'): (v or '').strip() for k, v in row.items()}
    for name in names:
        value = normalized.get(name)
        if value:
            return value
    return ''


@user_passes_test(is_admin_or_teacher)
def import_questions(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)

    if request.user.role == 'teacher' and not exam.batches.filter(teacher__user=request.user).exists():
        return redirect('exam_list')

    if request.method == 'POST':
        uploaded_file = request.FILES.get('csv_file')
        if not uploaded_file:
            messages.error(request, "Please choose a CSV file to upload.")
            return redirect('import_questions', exam_id=exam.id)

        if not uploaded_file.name.lower().endswith('.csv'):
            messages.error(request, "Only CSV files are supported.")
            return redirect('import_questions', exam_id=exam.id)

        try:
            decoded_file = uploaded_file.read().decode('utf-8-sig')
        except UnicodeDecodeError:
            messages.error(request, "Unable to read this CSV. Please save it as UTF-8 CSV and try again.")
            return redirect('import_questions', exam_id=exam.id)

        reader = csv.DictReader(io.StringIO(decoded_file))
        if not reader.fieldnames:
            messages.error(request, "The CSV file is empty or missing a header row.")
            return redirect('import_questions', exam_id=exam.id)

        imported_count = 0
        skipped_rows = []

        for row_number, row in enumerate(reader, start=2):
            question_text = _get_csv_value(row, 'question_text', 'question', 'title')
            marks_text = _get_csv_value(row, 'marks', 'mark')
            correct_value = _get_csv_value(row, 'correct_option', 'correct_answer', 'answer', 'is_correct')
            option_values = []
            option_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h']

            for index in range(1, 9):
                letter = option_letters[index - 1]
                option_text = _get_csv_value(
                    row,
                    f'option_{index}',
                    f'option{index}',
                    f'option_{letter}',
                    f'option{letter}',
                    f'answer_{index}',
                    f'answer{index}',
                    f'answer_{letter}',
                    f'answer{letter}',
                    f'choice_{index}',
                    f'choice_{letter}',
                    letter,
                )
                if option_text:
                    option_values.append(option_text)

            if not question_text or len(option_values) < 2 or not correct_value:
                skipped_rows.append(str(row_number))
                continue

            try:
                marks = int(marks_text) if marks_text else 1
            except ValueError:
                marks = 1

            correct_index = None
            if correct_value.isdigit():
                numeric_index = int(correct_value)
                if 1 <= numeric_index <= len(option_values):
                    correct_index = numeric_index - 1
                elif 0 <= numeric_index < len(option_values):
                    correct_index = numeric_index
            else:
                lowered_correct = correct_value.lower()
                letter_map = {'a': 0, 'b': 1, 'c': 2, 'd': 3}
                if lowered_correct in letter_map and letter_map[lowered_correct] < len(option_values):
                    correct_index = letter_map[lowered_correct]
                else:
                    for index, option_text in enumerate(option_values):
                        if option_text.strip().lower() == lowered_correct:
                            correct_index = index
                            break

            if correct_index is None:
                skipped_rows.append(str(row_number))
                continue

            question = Question.objects.create(
                exam=exam,
                question_text=question_text,
                marks=max(marks, 1)
            )

            for index, option_text in enumerate(option_values):
                Option.objects.create(
                    question=question,
                    text=option_text,
                    is_correct=(index == correct_index)
                )

            imported_count += 1

        if imported_count:
            exam.total_questions = exam.questions.count()
            exam.save(update_fields=['total_questions'])
            messages.success(request, f"Imported {imported_count} question(s) successfully.")

        if skipped_rows:
            messages.warning(request, f"Skipped row(s): {', '.join(skipped_rows)}. Check question, options, and correct answer.")
        elif not imported_count:
            messages.error(request, "No valid questions were found in the CSV.")

        return redirect('question_list', exam_id=exam.id)

    return render(request, 'exam/import_questions.html', {'exam': exam})


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


@user_passes_test(is_admin_center_or_teacher)
def exam_detail(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    
    exam = get_object_or_404(Exam, id=exam_id)

    # Check center/teacher isolation
    if is_center:
        if not exam.batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied: This exam is not assigned to your center's batches.")
        batches = exam.batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True)
    elif is_teacher:
        from apps.teachers.models import TeacherProfile
        profile = TeacherProfile.objects.filter(user=request.user).first()
        if not profile or not exam.batches.filter(teacher=profile).exists():
            return redirect('exam_list')
        batches = exam.batches.filter(teacher=profile)
    else:
        batches = exam.batches.all()

    # Student Count: count of unique students in batches assigned to this exam
    from apps.students.models import StudentProfile
    if is_center:
        student_count = StudentProfile.objects.filter(batch__in=batches, batch__center=request.user.center).count()
        attempts = exam.attempts.filter(student__studentprofile__batch__center=request.user.center)
    elif is_teacher:
        student_count = StudentProfile.objects.filter(batch__in=batches, batch__teacher=profile).count()
        attempts = exam.attempts.filter(student__studentprofile__batch__teacher=profile)
    else:
        student_count = StudentProfile.objects.filter(batch__in=batches).count()
        attempts = exam.attempts.all()

    # Metrics
    attempt_count = attempts.count()
    completed_attempts = attempts.filter(is_completed=True)
    completed_count = completed_attempts.count()
    
    if completed_count > 0:
        stats = completed_attempts.aggregate(
            avg_score=Avg('score'),
            high_score=Max('score'),
            low_score=Min('score')
        )
        avg_score = stats['avg_score'] or 0.0
        highest_score = stats['high_score'] or 0.0
        lowest_score = stats['low_score'] or 0.0
        
        pass_threshold = (exam.pass_percentage / 100.0) * exam.total_marks
        pass_count = completed_attempts.filter(score__gte=pass_threshold).count()
        fail_count = completed_count - pass_count
    else:
        avg_score = 0.0
        highest_score = 0.0
        lowest_score = 0.0
        pass_count = 0
        fail_count = 0

    return render(request, 'exam/exam_detail.html', {
        'exam': exam,
        'batches': batches,
        'student_count': student_count,
        'attempt_count': attempt_count,
        'avg_score': round(avg_score, 1),
        'highest_score': round(highest_score, 1),
        'lowest_score': round(lowest_score, 1),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'is_center': is_center,
    })


@login_required
def center_exam_results(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")
        
    exam = get_object_or_404(Exam, id=exam_id)
    
    # Check center isolation
    if is_center:
        if not exam.batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied: Exam belongs to another center.")
            
    attempts = exam.attempts.select_related('student__studentprofile__batch').all()
    if is_center:
        attempts = attempts.filter(student__studentprofile__batch__center=request.user.center)
        
    # Filter by batch
    batch_id = request.GET.get('batch', '').strip()
    if batch_id:
        # Verify batch belongs to center
        if is_center and not Batch.objects.filter(id=batch_id, course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied: Batch belongs to another center.")
        attempts = attempts.filter(student__studentprofile__batch_id=batch_id)
        
    # Analytics for this exam results:
    completed_attempts = attempts.filter(is_completed=True)
    completed_count = completed_attempts.count()
    if completed_count > 0:
        stats = completed_attempts.aggregate(
            avg_score=Avg('score'),
            high_score=Max('score'),
            low_score=Min('score')
        )
        avg_score = stats['avg_score'] or 0.0
        highest_score = stats['high_score'] or 0.0
        lowest_score = stats['low_score'] or 0.0
        
        pass_threshold = (exam.pass_percentage / 100.0) * exam.total_marks
        pass_count = completed_attempts.filter(score__gte=pass_threshold).count()
        fail_count = completed_count - pass_count
    else:
        avg_score = 0.0
        highest_score = 0.0
        lowest_score = 0.0
        pass_count = 0
        fail_count = 0
        
    if is_center:
        batches = exam.batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True)
    else:
        batches = exam.batches.all()
        
    return render(request, 'exam/center_exam_results.html', {
        'exam': exam,
        'attempts': attempts,
        'batches': batches,
        'selected_batch': batch_id,
        'avg_score': round(avg_score, 1),
        'highest_score': round(highest_score, 1),
        'lowest_score': round(lowest_score, 1),
        'pass_count': pass_count,
        'fail_count': fail_count,
        'is_center': is_center,
    })


@login_required
def center_attempts_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")
        
    attempts_qs = StudentExamAttempt.objects.select_related('student__studentprofile__batch__course', 'exam').order_by('-start_time')
    
    if is_center:
        attempts_qs = attempts_qs.filter(student__studentprofile__batch__center=request.user.center)
        
    # Search / Filters
    query = request.GET.get('q', '').strip()
    batch_id = request.GET.get('batch', '').strip()
    exam_id = request.GET.get('exam', '').strip()
    
    if query:
        attempts_qs = attempts_qs.filter(student__studentprofile__full_name__icontains=query)
    if batch_id:
        if is_center and not Batch.objects.filter(id=batch_id, course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied: Batch belongs to another center.")
        attempts_qs = attempts_qs.filter(student__studentprofile__batch_id=batch_id)
    if exam_id:
        if is_center and not Exam.objects.filter(id=exam_id, batches__course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied: Exam belongs to another center.")
        attempts_qs = attempts_qs.filter(exam_id=exam_id)
        
    # Pagination
    paginator = Paginator(attempts_qs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Filter dropdown options
    if is_center:
        batches = Batch.objects.filter(course__assignments__center=request.user.center, course__assignments__is_active=True)
        exams = Exam.objects.filter(batches__course__assignments__center=request.user.center, course__assignments__is_active=True).distinct()
    else:
        batches = Batch.objects.all()
        exams = Exam.objects.all()
        
    return render(request, 'exam/center_attempts_list.html', {
        'page_obj': page_obj,
        'batches': batches,
        'exams': exams,
        'query': query,
        'selected_batch': batch_id,
        'selected_exam': exam_id,
        'is_center': is_center,
    })


@login_required
def center_attempt_detail(request, attempt_id):
    attempt = get_object_or_404(StudentExamAttempt, id=attempt_id)
    user = request.user
    
    is_authorized = False
    if user.role == 'admin':
        is_authorized = True
    elif user.role == 'center':
        if attempt.student.studentprofile.batch and CenterCourseAssignment.objects.filter(
                center=user.center, course=attempt.student.studentprofile.batch.course).exists():
            is_authorized = True
    elif user.role == 'student':
        if attempt.student == user:
            is_authorized = True
            
    if not is_authorized:
        return HttpResponseForbidden("Access Denied: You are not authorized to view this attempt.")
        
    answers = attempt.answers.select_related('question').all()
    
    # Compute percentage
    percentage = (attempt.score / attempt.exam.total_marks * 100) if attempt.exam.total_marks > 0 else 0.0
    
    return render(request, 'exam/attempt_detail.html', {
        'attempt': attempt,
        'answers': answers,
        'percentage': round(percentage, 1),
    })


@login_required
def export_exam_results_csv(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")
        
    exam = get_object_or_404(Exam, id=exam_id)
    if is_center:
        if not exam.batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True).exists():
            return HttpResponseForbidden("Access Denied.")
            
    attempts = exam.attempts.select_related('student__studentprofile__batch').all()
    if is_center:
        attempts = attempts.filter(student__studentprofile__batch__center=request.user.center)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="exam_{exam_id}_results.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Batch', 'Score', 'Max Marks', 'Percentage', 'Status', 'Date Submitted'])
    
    for att in attempts.order_by('-start_time'):
        pct = (att.score / exam.total_marks * 100) if exam.total_marks > 0 else 0.0
        writer.writerow([
            att.student.studentprofile.full_name,
            att.student.studentprofile.batch.name if att.student.studentprofile.batch else 'N/A',
            att.score,
            exam.total_marks,
            f"{pct:.1f}%",
            'Completed' if att.is_completed else 'In Progress',
            att.submitted_at.strftime('%Y-%m-%d %H:%M') if att.is_completed else '-'
        ])
    return response


@login_required
def export_student_performance_csv(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")
        
    students = StudentProfile.objects.select_related('batch__course').all()
    if is_center:
        students = students.filter(batch__center=request.user.center)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="student_performance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Batch', 'Course', 'Exams Attempted', 'Average Score (%)'])
    
    for s in students.order_by('full_name'):
        attempts = StudentExamAttempt.objects.filter(student=s.user, is_completed=True)
        attempt_count = attempts.count()
        
        total_pct = 0.0
        for att in attempts:
            max_marks = att.exam.total_marks
            pct = (att.score / max_marks * 100) if max_marks > 0 else 0.0
            total_pct += pct
        avg_pct = (total_pct / attempt_count) if attempt_count > 0 else 0.0
        
        writer.writerow([
            s.full_name,
            s.batch.name if s.batch else 'N/A',
            s.batch.course.name if (s.batch and s.batch.course) else 'N/A',
            attempt_count,
            f"{avg_pct:.1f}%"
        ])
    return response


@login_required
def export_batch_performance_csv(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    
    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")
        
    batches = Batch.objects.select_related('course').all()
    if is_center:
        batches = batches.filter(course__assignments__center=request.user.center, course__assignments__is_active=True)
        
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="batch_performance.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Batch Name', 'Course', 'Students Count', 'Total Attempts', 'Average Score (%)', 'Pass Rate (%)'])
    
    for b in batches.order_by('name'):
        students_qs = StudentProfile.objects.filter(batch=b)
        students_count = students_qs.count()
        
        attempts = StudentExamAttempt.objects.filter(student__studentprofile__batch=b, is_completed=True)
        attempt_count = attempts.count()
        
        total_pct = 0.0
        passed_count = 0
        for att in attempts:
            max_marks = att.exam.total_marks
            pct = (att.score / max_marks * 100) if max_marks > 0 else 0.0
            total_pct += pct
            
            pass_threshold = (att.exam.pass_percentage / 100.0) * max_marks
            if att.score >= pass_threshold:
                passed_count += 1
                
        avg_pct = (total_pct / attempt_count) if attempt_count > 0 else 0.0
        pass_rate = (passed_count / attempt_count * 100) if attempt_count > 0 else 0.0
        
        writer.writerow([
            b.name,
            b.course.name,
            students_count,
            attempt_count,
            f"{avg_pct:.1f}%",
            f"{pass_rate:.1f}%"
        ])
    return response


def _ordered_subjects_for_schedule(course, duration=''):
    subjects_qs = Subject.objects.filter(course=course)
    if duration:
        duration_qs = subjects_qs.filter(duration_offset=duration)
        if duration_qs.exists():
            subjects_qs = duration_qs

    orders = {
        item.subject_id: item.order
        for item in SubjectOrder.objects.filter(course=course)
    }
    subjects = list(subjects_qs)
    subjects.sort(key=lambda item: (orders.get(item.id, 999999), -item.id))
    return subjects


def _build_schedule_subject_rows(schedule, post_data):
    subject_ids = post_data.getlist('subject_ids[]') or post_data.getlist('subject_ids')
    if len(subject_ids) == 1 and ',' in subject_ids[0]:
        subject_ids = [sid.strip() for sid in subject_ids[0].split(',') if sid.strip()]

    if not subject_ids:
        return [], 'Please add at least one subject schedule row.'

    allowed_subjects = {
        str(subject.id): subject
        for subject in _ordered_subjects_for_schedule(schedule.course, schedule.duration)
    }
    rows = []

    for index, subject_id in enumerate(subject_ids, start=1):
        subject = allowed_subjects.get(str(subject_id))
        if not subject:
            return [], 'Selected subject does not belong to the selected course.'

        exam_date = post_data.get(f'exam_date_{subject_id}', '').strip()
        exam_time = post_data.get(f'exam_time_{subject_id}', '').strip()
        if not exam_date or not exam_time:
            return [], f'Please enter date and time for {subject.name}.'

        rows.append(ExamScheduleSubject(
            schedule=schedule,
            subject=subject,
            exam_date=exam_date,
            exam_time=exam_time,
            order=index,
        ))

    return rows, ''


@admin_required
def ajax_exam_schedule_subjects(request):
    course_id = request.GET.get('course_id')
    duration = request.GET.get('duration', '').strip()

    try:
        course = Course.objects.get(pk=course_id)
    except (Course.DoesNotExist, TypeError, ValueError):
        return JsonResponse({'subjects': []})

    all_subjects = _ordered_subjects_for_schedule(course)
    durations = []
    seen_durations = set()
    for subject in all_subjects:
        if subject.duration_offset and subject.duration_offset not in seen_durations:
            seen_durations.add(subject.duration_offset)
            durations.append(subject.duration_offset)

    subjects = _ordered_subjects_for_schedule(course, duration)
    return JsonResponse({
        'durations': durations,
        'subjects': [
            {
                'id': subject.id,
                'name': subject.name,
                'code': subject.subject_code,
                'duration': subject.duration_offset,
            }
            for subject in subjects
        ]
    })


@admin_required
def exam_schedule_list(request):
    form = ExamScheduleForm()

    if request.method == 'POST':
        form = ExamScheduleForm(request.POST)
        if form.is_valid():
            schedule = form.save(commit=False)
            rows, row_error = _build_schedule_subject_rows(schedule, request.POST)
            if row_error:
                form.add_error(None, row_error)
                messages.error(request, row_error)
            else:
                with transaction.atomic():
                    schedule.save()
                    ExamScheduleSubject.objects.bulk_create(rows)
                messages.success(request, 'Schedule created successfully.')
                return redirect('exam_schedule_list')

    query = request.GET.get('q', '').strip()
    qs = ExamSchedule.objects.prefetch_related('subject_schedules__subject').all().order_by('-id')
    if query:
        qs = qs.filter(
            Q(course__name__icontains=query) |
            Q(center__name__icontains=query) |
            Q(exam_center__centre_name__icontains=query) |
            Q(session__session_name__icontains=query)
        )

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'exam/exam_schedule_list.html', {
        'form': form,
        'page_obj': page_obj,
        'query': query,
    })


@admin_required
def exam_schedule_edit(request, pk):
    schedule = get_object_or_404(ExamSchedule, pk=pk)

    if request.method == 'POST':
        form = ExamScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            schedule = form.save(commit=False)
            rows, row_error = _build_schedule_subject_rows(schedule, request.POST)
            if row_error:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'errors': {'subjects': [row_error]}}, status=400)
                form.add_error(None, row_error)
                messages.error(request, row_error)
                return redirect('exam_schedule_list')
            with transaction.atomic():
                schedule.save()
                ExamScheduleSubject.objects.filter(schedule=schedule).delete()
                ExamScheduleSubject.objects.bulk_create(rows)
            messages.success(request, 'Schedule updated successfully.')
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True})
            return redirect('exam_schedule_list')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: list(errs) for field, errs in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors}, status=400)
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'id': schedule.pk,
                'center': schedule.center.pk if schedule.center else '',
                'course': schedule.course.pk if schedule.course else '',
                'duration': schedule.duration,
                'exam_center': schedule.exam_center.pk if schedule.exam_center else '',
                'session': schedule.session.pk if schedule.session else '',
                'subjects': [
                    {
                        'id': row.subject_id,
                        'date': row.exam_date.isoformat(),
                        'time': row.exam_time.strftime('%H:%M'),
                    }
                    for row in schedule.subject_schedules.all()
                ],
            })
        form = ExamScheduleForm(instance=schedule)
    return redirect('exam_schedule_list')


@admin_required
def exam_schedule_delete(request, pk):
    schedule = get_object_or_404(ExamSchedule, pk=pk)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'Schedule deleted successfully.')
        return redirect('exam_schedule_list')
    return render(request, 'exam/exam_schedule_confirm_delete.html', {'schedule': schedule})

    # NOTE: All student views  → apps/students/views.py
    #       All teacher views  → apps/teachers/views.py


# ---------------------------------------------------------------------------
# Assign Exam To Center
# ---------------------------------------------------------------------------

@user_passes_test(is_admin)
def assign_exam_center_list(request):
    exams = Exam.objects.filter(is_published=True).select_related('course', 'center').prefetch_related('center_assignments__center').annotate(
        active_center_count=Count(
            'center_assignments',
            filter=Q(center_assignments__status=True, center_assignments__is_deleted=False),
            distinct=True
        )
    )

    q = request.GET.get('q', '').strip()
    if q:
        exams = exams.filter(
            Q(title__icontains=q) |
            Q(course__name__icontains=q) |
            Q(course_duration__icontains=q)
        )

    exams = exams.order_by('-id')

    show_entries = request.GET.get('show', '10')
    try:
        limit = int(show_entries)
    except ValueError:
        limit = 10

    paginator = Paginator(exams, limit)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    centers = Center.objects.all().order_by('name')

    return render(request, 'exam/assign_center_list.html', {
        'page_obj': page_obj,
        'centers': centers,
        'query': q,
        'show_entries': show_entries,
    })


@login_required
def ajax_get_exam_centers(request):
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)

    exam_id = request.GET.get('exam_id')
    if not exam_id:
        return JsonResponse({'success': False, 'message': 'Missing exam.'}, status=400)

    exam = get_object_or_404(Exam, id=exam_id)
    assigned_center_ids = set(
        ExamCenterAssignment.objects.filter(
            exam=exam,
            status=True,
            is_deleted=False
        ).values_list('center_id', flat=True)
    )

    centers = []
    for center in Center.objects.all().order_by('name'):
        centers.append({
            'id': center.id,
            'name': center.name,
            'code': center.code,
            'assigned': center.id in assigned_center_ids,
        })

    return JsonResponse({'success': True, 'centers': centers})


@login_required
def ajax_save_center_assignments(request):
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    import json
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        center_ids = data.get('center_ids', [])

        if not exam_id:
            return JsonResponse({'success': False, 'message': 'Missing exam.'}, status=400)

        exam = Exam.objects.get(id=exam_id)
        if not exam.is_published:
            return JsonResponse({'success': False, 'message': 'Only approved exams can be assigned to centers.'}, status=400)

        valid_center_ids = set(Center.objects.filter(id__in=center_ids).values_list('id', flat=True))

        with transaction.atomic():
            ExamCenterAssignment.all_objects.filter(exam=exam).exclude(center_id__in=valid_center_ids).update(status=False)

            assignments_saved = 0
            for center_id in valid_center_ids:
                obj, created = ExamCenterAssignment.all_objects.get_or_create(
                    exam=exam,
                    center_id=center_id,
                    defaults={'assigned_by': request.user, 'status': True, 'is_deleted': False}
                )
                if not created and (not obj.status or obj.is_deleted):
                    obj.status = True
                    obj.is_deleted = False
                    obj.deleted_at = None
                    obj.assigned_by = request.user
                    obj.save(update_fields=['status', 'is_deleted', 'deleted_at', 'assigned_by'])
                assignments_saved += 1

        return JsonResponse({'success': True, 'message': f'Successfully assigned exam to {assignments_saved} center(s).'})
    except Exam.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Exam not found.'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ---------------------------------------------------------------------------
# Assign Exam To Student
# ---------------------------------------------------------------------------

@user_passes_test(lambda u: u.is_authenticated and u.role in ['admin', 'center'])
def assign_exam_student_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if is_center:
        exams = Exam.objects.filter(is_published=True).filter(
            Q(center=request.user.center) |
            Q(center_assignments__center=request.user.center, center_assignments__status=True, center_assignments__is_deleted=False)
        ).distinct()
    else:
        exams = Exam.objects.filter(is_published=True)

    # Search filter
    q = request.GET.get('q', '').strip()
    if q:
        exams = exams.filter(
            Q(title__icontains=q) |
            Q(course__name__icontains=q) |
            Q(course_duration__icontains=q)
        )

    # Order by newest first
    exams = exams.order_by('-id')

    # Pagination
    show_entries = request.GET.get('show', '10')
    try:
        limit = int(show_entries)
    except ValueError:
        limit = 10

    paginator = Paginator(exams, limit)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'exam/assign_student_list.html', {
        'page_obj': page_obj,
        'centers': Center.objects.all().order_by('name') if is_admin else Center.objects.none(),
        'query': q,
        'show_entries': show_entries,
        'is_center': is_center,
        'is_admin': is_admin,
    })


@login_required
def ajax_get_eligible_students(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)

    exam_id = request.GET.get('exam_id')
    center_id = request.GET.get('center_id')
    course_id = request.GET.get('course_id')

    if not exam_id or not course_id:
        return JsonResponse({'success': False, 'message': 'Missing parameters.'}, status=400)

    try:
        exam = Exam.objects.get(id=exam_id)
        if not exam.is_published:
            return JsonResponse({'success': False, 'message': 'Only approved exams can be assigned to students.'}, status=400)

        # Verify access to exam
        if is_center and not (
            exam.center == request.user.center or
            ExamCenterAssignment.objects.filter(
                exam=exam,
                center=request.user.center,
                status=True,
                is_deleted=False
            ).exists()
        ):
            return JsonResponse({'success': False, 'message': 'Access Denied: You do not manage this exam.'}, status=403)
    except Exam.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Exam not found.'}, status=404)

    # Base query for students
    qs = StudentAdmission.objects.filter(status='Approved', course_id=course_id)

    # Apply center filter
    if is_center:
        qs = qs.filter(center=request.user.center)
    elif center_id:
        qs = qs.filter(center_id=center_id)

    # Exclude already assigned students
    assigned_student_ids = ExamStudentAssignment.objects.filter(exam=exam, status=True).values_list('student_id', flat=True)
    qs = qs.exclude(id__in=assigned_student_ids)

    students = []
    for s in qs:
        students.append({
            'id': s.id,
            'name': s.student_name,
            'reg_no': s.enrollment_no or 'N/A',
            'course': s.course.name if s.course else 'N/A',
            'center': s.center.name if s.center else 'N/A',
            'status': s.status
        })

    return JsonResponse({'success': True, 'students': students})


@login_required
def ajax_save_student_assignments(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid method.'}, status=405)

    import json
    from apps.fees.services import deduct_center_wallet_for_student_fee
    try:
        data = json.loads(request.body)
        exam_id = data.get('exam_id')
        student_ids = data.get('student_ids', [])

        if not exam_id or not student_ids:
            return JsonResponse({'success': False, 'message': 'Missing exam or students.'}, status=400)

        exam = Exam.objects.get(id=exam_id)
        if not exam.is_published:
            return JsonResponse({'success': False, 'message': 'Only approved exams can be assigned to students.'}, status=400)

        if is_center and not (
            exam.center == request.user.center or
            ExamCenterAssignment.objects.filter(
                exam=exam,
                center=request.user.center,
                status=True,
                is_deleted=False
            ).exists()
        ):
            return JsonResponse({'success': False, 'message': 'Access Denied: You do not manage this exam.'}, status=403)

        with transaction.atomic():
            assignments_to_save = []
            exam_fee_count = 0
            re_exam_fee_count = 0

            for s_id in student_ids:
                # Verify student belongs to center if role is center
                student = StudentAdmission.objects.select_related('center', 'user').get(id=s_id)
                if is_center and student.center != request.user.center:
                    continue

                existing_assignment = ExamStudentAssignment.all_objects.filter(exam=exam, student=student).first()
                if existing_assignment and existing_assignment.status and not existing_assignment.is_deleted:
                    continue

                assignments_to_save.append((student, existing_assignment))

                if is_center:
                    has_completed_attempt = bool(
                        student.user_id and StudentExamAttempt.objects.filter(
                            student_id=student.user_id,
                            exam=exam,
                            is_completed=True
                        ).exists()
                    )
                    if has_completed_attempt:
                        re_exam_fee_count += 1
                    else:
                        exam_fee_count += 1

            if is_center:
                deduct_center_wallet_for_student_fee(request.user.center, 'Exam Fees', exam_fee_count)
                deduct_center_wallet_for_student_fee(request.user.center, 'Re-Exam Fees', re_exam_fee_count)

            assignments_created = 0
            for student, existing_assignment in assignments_to_save:
                if existing_assignment:
                    existing_assignment.status = True
                    existing_assignment.is_deleted = False
                    existing_assignment.deleted_at = None
                    existing_assignment.assigned_by = request.user
                    existing_assignment.save(update_fields=['status', 'is_deleted', 'deleted_at', 'assigned_by'])
                else:
                    ExamStudentAssignment.objects.create(
                        exam=exam,
                        student=student,
                        assigned_by=request.user,
                        status=True
                    )
                assignments_created += 1

        return JsonResponse({'success': True, 'message': f'Successfully assigned {assignments_created} student(s) to the exam.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)



@login_required
def admin_student_exam_list(request):
    query = request.GET.get('q', '').strip()
    show_entries = request.GET.get('show', '10')

    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10
    
    queryset = StudentExamAttempt.objects.select_related(
        'student', 'exam', 'student__studentprofile', 'student__student_admission',
        'student__student_admission__course', 'exam__created_by', 'exam__course'
    ).prefetch_related('student__studentprofile__batch', 'exam__batches').all()

    # Role Based Access
    role = request.user.role
    if role == 'admin':
        pass
    elif role == 'center':
        queryset = queryset.filter(
            Q(student__student_admission__center=request.user.center) |
            Q(student__studentprofile__batch__center=request.user.center)
        )
    elif role == 'teacher':
        queryset = queryset.filter(exam__created_by=request.user)
    elif role == 'student':
        queryset = queryset.filter(student=request.user)
    else:
        queryset = queryset.none()

    if query:
        queryset = queryset.filter(
            Q(student__student_admission__student_name__icontains=query) |
            Q(student__studentprofile__full_name__icontains=query) |
            Q(student__username__icontains=query) |
            Q(exam__title__icontains=query)
        )

    queryset = queryset.order_by('-start_time')

    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'show_entries': str(per_page),
    }
    return render(request, 'exam/admin_student_exam_list.html', context)


@login_required
@require_POST
def delete_student_exam_attempt_ajax(request, pk):
    try:
        attempt = StudentExamAttempt.objects.get(pk=pk)
        
        # Check permissions
        role = request.user.role
        if role == 'admin':
            pass
        elif role == 'center':
            student_admission = getattr(attempt.student, 'student_admission', None)
            student_profile = getattr(attempt.student, 'studentprofile', None)
            is_owner = False
            if student_admission and student_admission.center == request.user.center:
                is_owner = True
            elif student_profile and student_profile.batch and student_profile.batch.center == request.user.center:
                is_owner = True
            if not is_owner:
                return JsonResponse({'success': False, 'message': 'Permission denied.'})
        elif role == 'teacher':
            if attempt.exam.created_by != request.user:
                return JsonResponse({'success': False, 'message': 'Permission denied.'})
        else:
            return JsonResponse({'success': False, 'message': 'Permission denied.'})
            
        attempt.delete() # SoftDeleteModel will handle soft deletion
        return JsonResponse({'success': True, 'message': 'Student exam attempt deleted successfully.'})
    except StudentExamAttempt.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Attempt not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@require_POST
def edit_student_exam_attempt_ajax(request, pk):
    from django.utils.dateparse import parse_datetime
    try:
        attempt = StudentExamAttempt.objects.get(pk=pk)
        
        # Check permissions
        role = request.user.role
        if role == 'admin':
            pass
        elif role == 'center':
            student_admission = getattr(attempt.student, 'student_admission', None)
            student_profile = getattr(attempt.student, 'studentprofile', None)
            is_owner = False
            if student_admission and student_admission.center == request.user.center:
                is_owner = True
            elif student_profile and student_profile.batch and student_profile.batch.center == request.user.center:
                is_owner = True
            if not is_owner:
                return JsonResponse({'success': False, 'message': 'Permission denied.'})
        elif role == 'teacher':
            if attempt.exam.created_by != request.user:
                return JsonResponse({'success': False, 'message': 'Permission denied.'})
        else:
            return JsonResponse({'success': False, 'message': 'Permission denied.'})

        # Load values from post
        attempt_time_str = request.POST.get('attempt_time', '').strip()
        score_str = request.POST.get('score', '').strip()

        if not attempt_time_str or not score_str:
            return JsonResponse({'success': False, 'message': 'Please fill all fields.'})

        # Prepend or parse timezone aware / naive datetime
        from django.utils import timezone
        attempt_time = parse_datetime(attempt_time_str)
        if not attempt_time:
            return JsonResponse({'success': False, 'message': 'Invalid date/time format.'})
        
        if timezone.is_naive(attempt_time):
            attempt_time = timezone.make_aware(attempt_time, timezone.get_current_timezone())

        try:
            score = float(score_str)
        except ValueError:
            return JsonResponse({'success': False, 'message': 'Invalid score percentage.'})

        # Update in database using update() to bypass auto_now un-writeability
        StudentExamAttempt.objects.filter(pk=pk).update(
            start_time=attempt_time,
            submitted_at=attempt_time,
            score=score
        )
        return JsonResponse({'success': True, 'message': 'Student exam attempt updated successfully.'})
    except StudentExamAttempt.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Attempt not found.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)


# ---------------------------------------------------------------------------
# Exam Centre CRUD — Admin only, independent from Center Information
# ---------------------------------------------------------------------------

@admin_required
def exam_centre_list(request):
    """
    List all Exam Centres and handle the Add form via POST.
    Admin-only. Completely independent from Center Information.
    """
    query = request.GET.get('q', '').strip()
    centres = ExamCentre.objects.all()
    if query:
        centres = centres.filter(
            Q(centre_name__icontains=query) |
            Q(centre_code__icontains=query) |
            Q(address__icontains=query)
        )

    if request.method == 'POST':
        centre_name = request.POST.get('centre_name', '').strip()
        centre_code = request.POST.get('centre_code', '').strip()
        address = request.POST.get('address', '').strip()
        is_active = request.POST.get('is_active') == 'on'

        errors = {}
        if not centre_name:
            errors['centre_name'] = 'Centre name is required.'
        if not centre_code:
            errors['centre_code'] = 'Centre code is required.'
        elif ExamCentre.objects.filter(centre_code__iexact=centre_code).exists():
            errors['centre_code'] = 'A centre with this code already exists.'
        if not address:
            errors['address'] = 'Address is required.'

        if not errors:
            ExamCentre.objects.create(
                centre_name=centre_name,
                centre_code=centre_code.upper(),
                address=address,
                is_active=is_active,
            )
            messages.success(request, f'Exam Centre "{centre_name}" created successfully.')
            return redirect('exam_centre_list')

        # Validation failed — re-render with errors and sticky values
        paginator = Paginator(centres, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)
        return render(request, 'exam/exam_centre_list.html', {
            'page_obj': page_obj,
            'query': query,
            'form_errors': errors,
            'form_data': request.POST,
        })

    paginator = Paginator(centres, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return render(request, 'exam/exam_centre_list.html', {
        'page_obj': page_obj,
        'query': query,
    })


@admin_required
def exam_centre_edit(request, pk):
    """
    AJAX endpoint:
      GET  → returns current field values as JSON
      POST → validates and saves updated fields, returns JSON
    """
    centre = get_object_or_404(ExamCentre, pk=pk)

    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'centre_name': centre.centre_name,
            'centre_code': centre.centre_code,
            'address': centre.address,
            'is_active': centre.is_active,
        })

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        centre_name = request.POST.get('centre_name', '').strip()
        centre_code = request.POST.get('centre_code', '').strip()
        address = request.POST.get('address', '').strip()
        is_active = request.POST.get('is_active') == 'true'

        errors = {}
        if not centre_name:
            errors['centre_name'] = ['Centre name is required.']
        if not centre_code:
            errors['centre_code'] = ['Centre code is required.']
        elif ExamCentre.objects.filter(centre_code__iexact=centre_code).exclude(pk=pk).exists():
            errors['centre_code'] = ['A centre with this code already exists.']
        if not address:
            errors['address'] = ['Address is required.']

        if errors:
            return JsonResponse({'success': False, 'errors': errors})

        centre.centre_name = centre_name
        centre.centre_code = centre_code.upper()
        centre.address = address
        centre.is_active = is_active
        centre.save()
        return JsonResponse({'success': True})

    return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)


@admin_required
def exam_centre_delete(request, pk):
    """
    Soft-deletes an Exam Centre. Accepts GET (redirect-based) or POST.
    Also handles AJAX DELETE / POST requests.
    """
    centre = get_object_or_404(ExamCentre, pk=pk)
    centre_name = centre.centre_name
    centre.delete()  # SoftDeleteModel.delete()
    messages.success(request, f'Exam Centre "{centre_name}" deleted successfully.')
    return redirect('exam_centre_list')
