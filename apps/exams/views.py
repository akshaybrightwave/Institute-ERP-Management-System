from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from .models import Exam, Question, Option, StudentAnswer, StudentExamAttempt, ExamSchedule
from .forms import ExamForm, QuestionForm, OptionForm, ExamScheduleForm
from apps.accounts.views import admin_required
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.utils.timezone import now
from django.db.models import Avg, Max, Min, Q, Count, F
from django.core.paginator import Paginator
from apps.centers.models import Center
from apps.courses.models import Course
from apps.academics.models import AcademicSession
from apps.students.models import StudentProfile
from apps.batches.models import Batch
import csv


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
        exams = Exam.objects.filter(center=request.user.center)
    elif is_teacher:
        exams = Exam.objects.filter(created_by=request.user)
    else:
        exams = Exam.objects.all()

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
            exam.created_by = request.user
            # Populate date field for backwards compatibility
            if exam.start_datetime:
                exam.date = exam.start_datetime.date()
            # If is_published comes as hidden "1", set it
            if request.POST.get('is_published') == '1':
                exam.is_published = True
            exam.save()
            form.save_m2m()
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

    if is_center and exam.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's exams.")

    if is_teacher:
        if exam.created_by != request.user:
            return HttpResponseForbidden("Access Denied: You did not create this exam.")

    if request.method == 'POST':
        form = ExamForm(request.POST, instance=exam, user=request.user)
        if form.is_valid():
            exam_obj = form.save(commit=False)
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
    return render(request, 'exam/edit_exam.html', {'form': form, 'exam': exam})


@login_required
def delete_exam(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied.")

    exam = get_object_or_404(Exam, id=exam_id)

    if is_center and exam.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You do not manage this center's exams.")

    exam.delete()
    messages.success(request, "Exam deleted successfully!")
    return redirect('exam_list')


@login_required
def ajax_toggle_exam_status(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    if not (is_admin or is_center):
        return JsonResponse({'success': False, 'message': 'Access Denied.'}, status=403)
    
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


@user_passes_test(is_admin_center_or_teacher)
def exam_detail(request, exam_id):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'
    
    exam = get_object_or_404(Exam, id=exam_id)

    # Check center/teacher isolation
    if is_center:
        if not exam.batches.filter(course__center=request.user.center).exists():
            return HttpResponseForbidden("Access Denied: This exam is not assigned to your center's batches.")
        batches = exam.batches.filter(course__center=request.user.center)
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
        student_count = StudentProfile.objects.filter(batch__in=batches, batch__course__center=request.user.center).count()
        attempts = exam.attempts.filter(student__studentprofile__batch__course__center=request.user.center)
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
        if not exam.batches.filter(course__center=request.user.center).exists():
            return HttpResponseForbidden("Access Denied: Exam belongs to another center.")
            
    attempts = exam.attempts.select_related('student__studentprofile__batch').all()
    if is_center:
        attempts = attempts.filter(student__studentprofile__batch__course__center=request.user.center)
        
    # Filter by batch
    batch_id = request.GET.get('batch', '').strip()
    if batch_id:
        # Verify batch belongs to center
        if is_center and not Batch.objects.filter(id=batch_id, course__center=request.user.center).exists():
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
        batches = exam.batches.filter(course__center=request.user.center)
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
        attempts_qs = attempts_qs.filter(student__studentprofile__batch__course__center=request.user.center)
        
    # Search / Filters
    query = request.GET.get('q', '').strip()
    batch_id = request.GET.get('batch', '').strip()
    exam_id = request.GET.get('exam', '').strip()
    
    if query:
        attempts_qs = attempts_qs.filter(student__studentprofile__full_name__icontains=query)
    if batch_id:
        if is_center and not Batch.objects.filter(id=batch_id, course__center=request.user.center).exists():
            return HttpResponseForbidden("Access Denied: Batch belongs to another center.")
        attempts_qs = attempts_qs.filter(student__studentprofile__batch_id=batch_id)
    if exam_id:
        if is_center and not Exam.objects.filter(id=exam_id, batches__course__center=request.user.center).exists():
            return HttpResponseForbidden("Access Denied: Exam belongs to another center.")
        attempts_qs = attempts_qs.filter(exam_id=exam_id)
        
    # Pagination
    paginator = Paginator(attempts_qs, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Filter dropdown options
    if is_center:
        batches = Batch.objects.filter(course__center=request.user.center)
        exams = Exam.objects.filter(batches__course__center=request.user.center).distinct()
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
        if attempt.student.studentprofile.batch and attempt.student.studentprofile.batch.course.center == user.center:
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
        if not exam.batches.filter(course__center=request.user.center).exists():
            return HttpResponseForbidden("Access Denied.")
            
    attempts = exam.attempts.select_related('student__studentprofile__batch').all()
    if is_center:
        attempts = attempts.filter(student__studentprofile__batch__course__center=request.user.center)
        
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
        students = students.filter(batch__course__center=request.user.center)
        
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
        batches = batches.filter(course__center=request.user.center)
        
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


@admin_required
def exam_schedule_list(request):
    form = ExamScheduleForm()

    if request.method == 'POST':
        form = ExamScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule created successfully.')
            return redirect('exam_schedule_list')

    query = request.GET.get('q', '').strip()
    qs = ExamSchedule.objects.all().order_by('-id')
    if query:
        qs = qs.filter(
            Q(course__name__icontains=query) |
            Q(center__name__icontains=query) |
            Q(exam_center__name__icontains=query) |
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
            form.save()
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
