import csv
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.contrib import messages
from django import forms
from django.db.models import Q
from django.db import transaction, models
from django.core.paginator import Paginator


from .models import Result, ResultMarks
from .forms import ResultForm
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession
from apps.subjects.models import Subject



def _handle_list_and_csv(request, is_center):
    qs = Result.objects.select_related('student', 'session', 'student__course', 'student__center').all()
    if is_center:
        qs = qs.filter(student__center=request.user.center)

    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(
            Q(student__student_name__icontains=query) |
            Q(student__enrollment_no__icontains=query) |
            Q(course_duration__icontains=query)
        )

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="exam_results.csv"'
        writer = csv.writer(response)
        writer.writerow(['Enrollment No', 'Student Name', 'Course', 'Course Duration', 'Institute', 'Result Type'])
        for r in qs:
            writer.writerow([
                r.student.enrollment_no,
                r.student.student_name,
                r.student.course.name if r.student.course else '',
                r.course_duration,
                r.student.center.name if r.student.center else '',
                r.result_type,
            ])
        return response, True

    show_entries = request.GET.get('show', '10')
    try:
        per_page = int(show_entries)
    except ValueError:
        per_page = 10

    paginator = Paginator(qs.order_by('-created_at', '-id'), per_page)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return {
        'page_obj': page_obj,
        'query': query,
        'show_entries': show_entries,
    }, False


@login_required
def result_list(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'

    if not (is_admin or is_center or is_teacher):
        return HttpResponseForbidden("Access Denied: Unauthorized role.")

    res = _handle_list_and_csv(request, is_center)
    if res[1]:
        return res[0]

    context = res[0]
    context.update({
        'is_admin': is_admin,
        'is_center': is_center,
        'is_teacher': is_teacher,
    })
    return render(request, 'results/result_list.html', context)


@login_required
def result_create(request):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Only Admin or Center can access.")

    form = ResultForm(user=request.user)
    selected_student_obj = None
    validation_errors = {}

    if request.method == 'POST':
        post_data = request.POST.copy()
        if is_center:
            post_data['center'] = request.user.center.id

        form = ResultForm(post_data, user=request.user)
        if form.is_valid():
            try:
                with transaction.atomic():
                    result_obj = form.save(commit=False)
                    result_obj.session = form.cleaned_data['session']
                    
                    duration_val = result_obj.course_duration
                    if 'Year' in duration_val:
                        result_obj.result_type = 'Yearly'
                    else:
                        result_obj.result_type = 'Semester'
                        
                    result_obj.created_by = request.user
                    
                    # Fetch subjects to validate and store marks
                    subjects = Subject.objects.filter(
                        course=result_obj.student.course,
                        duration_offset=result_obj.course_duration
                    )
                    
                    if not subjects.exists():
                        raise Exception("No subjects are configured for this course's duration in the system. Please add subjects before generating a result.")

                    total_max = 0
                    total_obtained = 0
                    is_pass = True

                    # We save the parent Result first so we can attach ResultMarks
                    result_obj.save()

                    for subject in subjects:
                        theory_input = f'obtain_theory_{subject.id}'
                        practical_input = f'obtain_practical_{subject.id}'
                        
                        rmarks = ResultMarks(result=result_obj, subject=subject)

                        # Validate Theory
                        if subject.subject_type in ['Theory', 'Both']:
                            theory_val = request.POST.get(theory_input, '').strip()
                            if theory_val == '':
                                validation_errors[theory_input] = "This field is required."
                            else:
                                try:
                                    theory_marks = int(theory_val)
                                    if theory_marks < 0:
                                        validation_errors[theory_input] = "Marks cannot be negative."
                                    elif theory_marks > (subject.theory_max_marks or 100):
                                        validation_errors[theory_input] = f"Marks cannot exceed max marks ({subject.theory_max_marks or 100})."
                                    else:
                                        rmarks.obtained_theory_marks = theory_marks
                                        total_obtained += theory_marks
                                        # Pass/Fail check
                                        if subject.theory_min_marks and theory_marks < subject.theory_min_marks:
                                            is_pass = False
                                except ValueError:
                                    validation_errors[theory_input] = "Must be a valid integer."
                            total_max += subject.theory_max_marks or 100

                        # Validate Practical
                        if subject.subject_type in ['Practical', 'Both']:
                            practical_val = request.POST.get(practical_input, '').strip()
                            if practical_val == '':
                                validation_errors[practical_input] = "This field is required."
                            else:
                                try:
                                    practical_marks = int(practical_val)
                                    if practical_marks < 0:
                                        validation_errors[practical_input] = "Marks cannot be negative."
                                    elif practical_marks > (subject.practical_max_marks or 100):
                                        validation_errors[practical_input] = f"Marks cannot exceed max marks ({subject.practical_max_marks or 100})."
                                    else:
                                        rmarks.obtained_practical_marks = practical_marks
                                        total_obtained += practical_marks
                                        # Pass/Fail check
                                        if subject.practical_min_marks and practical_marks < subject.practical_min_marks:
                                            is_pass = False
                                except ValueError:
                                    validation_errors[practical_input] = "Must be a valid integer."
                            total_max += subject.practical_max_marks or 100

                        if not validation_errors:
                            rmarks.save()

                    if validation_errors:
                        # Force rollback
                        raise Exception("Validation failed on subject marks.")

                    # Calculate and save aggregates
                    result_obj.total_max_marks = total_max
                    result_obj.total_obtained_marks = total_obtained
                    if total_max > 0:
                        result_obj.percentage = round((total_obtained / total_max) * 100, 2)
                    result_obj.status_pass_fail = 'Pass' if is_pass else 'Fail'
                    result_obj.save()

                    messages.success(request, 'Result published successfully.')
                    return redirect('result_list')

            except Exception as e:
                # If it's a validation error we raised, pass it through
                if not validation_errors:
                    messages.error(request, str(e))
                else:
                    messages.error(request, 'Please correct the errors below.')
        else:
            messages.error(request, 'Please correct the errors below.')

        student_id = request.POST.get('student')
        if student_id:
            try:
                selected_student_obj = StudentAdmission.objects.get(id=student_id)
            except StudentAdmission.DoesNotExist:
                pass

    res = _handle_list_and_csv(request, is_center)
    if res[1]:
        return res[0]

    context = res[0]
    context.update({
        'form': form,
        'is_admin': is_admin,
        'is_center': is_center,
        'selected_student_obj': selected_student_obj,
        'validation_errors': validation_errors,
    })
    return render(request, 'results/result_create.html', context)


@login_required
def result_view(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'
    is_teacher = request.user.role == 'teacher'

    result_obj = get_object_or_404(
        Result.objects.select_related('student', 'session', 'student__course', 'student__center'),
        pk=pk
    )

    if is_center and result_obj.student.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You cannot view results for other centers.")

    # Get stored subject-wise marks
    marks = ResultMarks.objects.filter(result=result_obj).select_related('subject')

    rows = []
    for m in marks:
        if m.subject.subject_type in ['Theory', 'Both']:
            rows.append({
                'code': m.subject.subject_code,
                'name': m.subject.name,
                'type': 'Theory',
                'min': m.subject.theory_min_marks or 35,
                'max': m.subject.theory_max_marks or 100,
                'obtained': m.obtained_theory_marks,
                'status': 'Pass' if (not m.subject.theory_min_marks or (m.obtained_theory_marks and m.obtained_theory_marks >= m.subject.theory_min_marks)) else 'Fail'
            })
        if m.subject.subject_type in ['Practical', 'Both']:
            rows.append({
                'code': m.subject.subject_code,
                'name': m.subject.name,
                'type': 'Practical',
                'min': m.subject.practical_min_marks or 35,
                'max': m.subject.practical_max_marks or 100,
                'obtained': m.obtained_practical_marks,
                'status': 'Pass' if (not m.subject.practical_min_marks or (m.obtained_practical_marks and m.obtained_practical_marks >= m.subject.practical_min_marks)) else 'Fail'
            })

    return render(request, 'results/result_view.html', {
        'result': result_obj,
        'rows': rows,
        'is_admin': is_admin,
        'is_center': is_center,
        'is_teacher': is_teacher,
    })


@login_required
def result_delete(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Unauthorized.")

    result_obj = get_object_or_404(Result, pk=pk)
    if is_center and result_obj.student.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You cannot delete results for other centers.")

    if request.method == 'POST':
        student_name = result_obj.student.student_name
        result_obj.delete()
        messages.success(request, f"Result for {student_name} deleted successfully.")
        
    return redirect('result_list')



@login_required
def get_student_duration_choices(request):
    student_id = request.GET.get('student_id')
    if not student_id:
        return JsonResponse({'choices': []})

    try:
        if request.user.role == 'center':
            student = StudentAdmission.objects.get(id=student_id, center=request.user.center)
        else:
            student = StudentAdmission.objects.get(id=student_id)
            
        duration_str = student.course.duration if student.course else ''
        
        # Instantiate form to reuse parsing logic
        form = ResultForm(user=request.user)
        choices = form._parse_duration_choices(duration_str)
        return JsonResponse({'choices': choices})
    except StudentAdmission.DoesNotExist:
        return JsonResponse({'choices': []})


@login_required
def get_subjects_for_duration(request):
    student_id = request.GET.get('student_id')
    duration = request.GET.get('duration')
    if not student_id or not duration:
        return JsonResponse({'subjects': []})
        
    try:
        if request.user.role == 'center':
            student = StudentAdmission.objects.get(id=student_id, center=request.user.center)
        else:
            student = StudentAdmission.objects.get(id=student_id)
            
        subjects = Subject.objects.filter(course=student.course, duration_offset=duration)
        
        # DEBUG PRINTS AS REQUESTED
        print("====== DEBUG INFO ======")
        print(f"Student ID: {student.id}")
        print(f"Course ID: {student.course.id if student.course else None}")
        print(f"Course Name: {student.course.name if student.course else None}")
        print(f"Duration Selected: '{duration}'")
        print(f"Subject Count: {subjects.count()}")
        print(f"Matching Subject IDs: {[s.id for s in subjects]}")
        try:
            print(f"SQL Query: {subjects.query}")
        except Exception as e:
            print(f"Could not print SQL: {e}")
        print("========================")
        
        
        rows = []
        for s in subjects:
            if s.subject_type in ['Theory', 'Both']:
                rows.append({
                    'id': s.id,
                    'code': s.subject_code,
                    'name': s.name,
                    'type': 'Theory',
                    'min': s.theory_min_marks or 35,
                    'max': s.theory_max_marks or 100,
                    'input_name': f'obtain_theory_{s.id}'
                })
            if s.subject_type in ['Practical', 'Both']:
                rows.append({
                    'id': s.id,
                    'code': s.subject_code,
                    'name': s.name,
                    'type': 'Practical',
                    'min': s.practical_min_marks or 35,
                    'max': s.practical_max_marks or 100,
                    'input_name': f'obtain_practical_{s.id}'
                })
        return JsonResponse({'subjects': rows})
    except Exception:
        return JsonResponse({'subjects': []})


@login_required
def student_results_autocomplete(request):
    q = request.GET.get('q', '').strip()
    center_id = request.GET.get('center_id', '').strip()

    results = []
    if q:
        qs = StudentAdmission.objects.filter(
            Q(enrollment_no__icontains=q) |
            Q(student_name__icontains=q) |
            Q(whatsapp_no__icontains=q)
        ).filter(status='Approved')

        if request.user.role == 'center':
            qs = qs.filter(center=request.user.center)
        elif center_id:
            qs = qs.filter(center_id=center_id)

        qs = qs.select_related('center')[:20]

        for s in qs:
            results.append({
                'id': s.id,
                'db_id': s.id,
                'text': f'{s.student_name} ({s.enrollment_no})',
                'name': s.student_name,
                'enrollment': s.enrollment_no,
                'mobile': s.whatsapp_no,
            })
            
    return JsonResponse({'results': results})


@login_required
def result_edit(request, pk):
    is_admin = request.user.role == 'admin'
    is_center = request.user.role == 'center'

    if not (is_admin or is_center):
        return HttpResponseForbidden("Access Denied: Unauthorized.")

    result_obj = get_object_or_404(
        Result.objects.select_related('student', 'session', 'student__course', 'student__center'),
        pk=pk
    )

    if is_center and result_obj.student.center != request.user.center:
        return HttpResponseForbidden("Access Denied: You cannot edit results for other centers.")

    # Fetch subjects matching student course and stage (course_duration)
    subjects = Subject.objects.filter(
        course=result_obj.student.course,
        duration_offset=result_obj.course_duration
    )

    # Fetch existing marks or map them
    marks_qs = ResultMarks.objects.filter(result=result_obj)
    marks_map = {m.subject_id: m for m in marks_qs}

    if request.method == 'POST':
        # Update Issue Date
        issue_date_str = request.POST.get('issue_date')
        if issue_date_str:
            result_obj.issue_date = issue_date_str
            result_obj.save()

        # Update obtained marks for each subject
        for subject in subjects:
            theory_val = request.POST.get(f'obtain_theory_{subject.id}')
            practical_val = request.POST.get(f'obtain_practical_{subject.id}')

            # Create or update ResultMarks
            rmarks_obj = marks_map.get(subject.id)
            if not rmarks_obj:
                rmarks_obj = ResultMarks(result=result_obj, subject=subject)

            if theory_val is not None and theory_val.strip() != '':
                try:
                    rmarks_obj.obtained_theory_marks = int(theory_val)
                except ValueError:
                    pass
            else:
                rmarks_obj.obtained_theory_marks = None

            if practical_val is not None and practical_val.strip() != '':
                try:
                    rmarks_obj.obtained_practical_marks = int(practical_val)
                except ValueError:
                    pass
            else:
                rmarks_obj.obtained_practical_marks = None

            rmarks_obj.save()

        messages.success(request, 'Marksheet updated successfully.')
        return redirect('result_list')

    # Prepare rows for the table:
    rows = []
    total_max = 0
    total_obtained = 0

    for subject in subjects:
        rmarks = marks_map.get(subject.id)
        
        # Add Theory component if applicable
        if subject.subject_type in ['Theory', 'Both']:
            theory_obtained = rmarks.obtained_theory_marks if rmarks else None
            rows.append({
                'subject_id': subject.id,
                'code': subject.subject_code,
                'name': subject.name,
                'type': 'Theory',
                'min': subject.theory_min_marks or 35,
                'max': subject.theory_max_marks or 100,
                'obtained': theory_obtained,
                'input_name': f'obtain_theory_{subject.id}'
            })
            total_max += subject.theory_max_marks or 100
            if theory_obtained is not None:
                total_obtained += theory_obtained

        # Add Practical component if applicable
        if subject.subject_type in ['Practical', 'Both']:
            practical_obtained = rmarks.obtained_practical_marks if rmarks else None
            rows.append({
                'subject_id': subject.id,
                'code': subject.subject_code,
                'name': subject.name,
                'type': 'Practical',
                'min': subject.practical_min_marks or 35,
                'max': subject.practical_max_marks or 100,
                'obtained': practical_obtained,
                'input_name': f'obtain_practical_{subject.id}'
            })
            total_max += subject.practical_max_marks or 100
            if practical_obtained is not None:
                total_obtained += practical_obtained

    context = {
        'result': result_obj,
        'rows': rows,
        'total_max': total_max,
        'total_obtained': total_obtained,
        'is_admin': is_admin,
        'is_center': is_center,
    }
    return render(request, 'results/result_edit.html', context)

