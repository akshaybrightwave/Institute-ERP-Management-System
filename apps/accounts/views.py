from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from .forms import AdminSignupForm, FeedbackForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages  

from django.core.paginator import Paginator
from django.db.models import Q
from apps.exams.models import Exam
from apps.teachers.models import TeacherProfile

# Create your views here.

def home(request):
    exams = Exam.objects.order_by('-date', '-id')  # fallback by id if date same
    paginator = Paginator(exams, 3)  # 3 exams per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'accounts/home.html', {'page_obj': page_obj})

def signup_admin(request):
    if request.method == 'POST':
        form = AdminSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admin account created successfully. Please log in.')
            return redirect('login')
    else:
        form = AdminSignupForm()
    return render(request, 'accounts/signup_admin.html', {'form': form})



def signup_teacher(request):
    if request.method == 'POST':
        form = TeacherSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Teacher account created successfully. Please log in.')
            return redirect('login')
    else:
        form = TeacherSignupForm()
    return render(request, 'accounts/signup_teacher.html', {'form': form})

# from django.db import transaction
# # def signup_teacher(request):
#     if request.method == 'POST':
#         form = TeacherSignupForm(request.POST)
#         if form.is_valid():
#             try:
#                 with transaction.atomic():
#                     user = form.save()

#                     # Explicit TeacherProfile creation
#                     profile = TeacherProfile.objects.create(
#                         user=user,
#                         full_name=user.username,  # Ensure valid data
#                         email=user.email
#                     )

#                     print(f"TeacherProfile created for {user.username}")

#                 messages.success(request, 'Teacher account created successfully. Please log in.')
#                 return redirect('login')

#             except Exception as e:
#                 print('Error creating TeacherProfile:', e)
#                 messages.error(request, 'Something went wrong. Please try again.')

#     else:
#         form = TeacherSignupForm()

#     return render(request, 'accounts/signup_teacher.html', {'form': form})







def signup_student(request):
    if request.method == 'POST':
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student account created successfully. Please log in.')
            return redirect('login')
    else:
        form = StudentSignupForm()
    return render(request, 'accounts/signup_student.html', {'form': form})



def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, 'Please enter both username and password')
            return redirect('login')

        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('student_dashboard')
        else:
            messages.error(request, 'Invalid credentials')
            return redirect('login')

    return render(request, 'accounts/login.html')


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')



#to restrict views to User Admins

from django.http import HttpResponseForbidden
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        return HttpResponseForbidden("Access Denied: Admins only.")
    return wrapper



# Admin Dashboard and CRUD Views 

from django.shortcuts import get_object_or_404
from .models import User, Feedback
from .forms import AdminSignupForm, TeacherSignupForm, StudentSignupForm, StudentEditForm, TeacherEditForm

@admin_required
def admin_dashboard(request):
    from apps.centers.models import Center
    from apps.courses.models import Course
    from apps.batches.models import Batch

    context = {
        'total_students': User.objects.filter(role='student').count(),
        'total_teachers': User.objects.filter(role='teacher').count(),
        'total_exams': Exam.objects.count(),
        'active_exams': Exam.objects.filter(is_published=True).count(),
        'batch_assigned_exams': Exam.objects.filter(batches__isnull=False).distinct().count(),
        'unread_feedback_count': Feedback.objects.filter(is_read=False).count(),
        'total_centers': Center.objects.count(),
        'total_courses': Course.objects.count(),
        'total_batches': Batch.objects.count(),
    }
    return render(request, 'accounts/admin_dashboard.html', context)

@admin_required
def user_list(request):
    users = User.objects.exclude(role='admin')

    query = request.GET.get('q', '').strip()
    role = request.GET.get('role', '').strip()
    selected_batch_id = request.GET.get('batch', '').strip()

    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query)
        )
    if role in ('student', 'teacher'):
        users = users.filter(role=role)
    if selected_batch_id:
        users = users.filter(studentprofile__batch_id=selected_batch_id)

    from apps.batches.models import Batch
    batches = Batch.objects.all()

    return render(request, 'accounts/user_list.html', {
        'users': users,
        'query': query,
        'role': role,
        'batches': batches,
        'selected_batch_id': selected_batch_id,
    })


@admin_required
def user_add(request):
    role = request.GET.get('role')
    if role == 'student':
        form_class = StudentSignupForm
    elif role == 'teacher':
        form_class = TeacherSignupForm
    else:
        return HttpResponseForbidden("Invalid role.")

    if request.method == 'POST':
        if role == 'student':
            form = form_class(request.POST, is_admin=True)
        else:
            form = form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect('user_list')
    else:
        if role == 'student':
            form = form_class(is_admin=True)
        else:
            form = form_class()

    return render(request, 'accounts/user_add.html', {'form': form, 'role': role})

@admin_required
def user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.role == 'student':
        form_class = StudentEditForm
    elif user.role == 'teacher':
        form_class = TeacherEditForm
    else:
        return HttpResponseForbidden("Invalid user type.")

    if request.method == 'POST':
        if user.role == 'student':
            form = form_class(request.POST, instance=user, is_admin=True)
        else:
            form = form_class(request.POST, instance=user)
        if form.is_valid():
            form.save()
            if user.role == 'student':
                messages.success(request, "Student updated successfully.")
            elif user.role == 'teacher':
                messages.success(request, "Teacher updated successfully.")
            return redirect('user_list')
    else:
        if user.role == 'student':
            form = form_class(instance=user, is_admin=True)
        else:
            form = form_class(instance=user)

    return render(request, 'accounts/user_edit.html', {'form': form, 'edited_user': user})


@admin_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.role == 'admin':
        return HttpResponseForbidden("Cannot delete admin user.")
    user.delete()
    return redirect('user_list')



#contact 
# def contact_view(request):
#     if request.method == 'POST':
#         form = FeedbackForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Thank you for your feedback!')
#             return redirect('contact')  
#     else:
#         form = FeedbackForm()
#     return render(request, 'accounts/contact.html', {'form': form})

def contact_view(request):
    if request.method=='POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Thank you for your feedback')
            return redirect('contact')
    else:
        form= FeedbackForm()
    return render(request,'accounts/contact.html',{'form':form})


# Admin Feedback Inbox

@admin_required
def feedback_list(request):
    feedbacks = Feedback.objects.all().order_by('-submitted_at')

    status = request.GET.get('status', '').strip()
    if status == 'unread':
        feedbacks = feedbacks.filter(is_read=False)

    paginator = Paginator(feedbacks, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'accounts/feedback_list.html', {
        'page_obj': page_obj,
        'status': status,
        'unread_count': Feedback.objects.filter(is_read=False).count(),
    })


@admin_required
def feedback_detail(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if not feedback.is_read:
        feedback.is_read = True
        feedback.save()
    return render(request, 'accounts/feedback_detail.html', {'feedback': feedback})


@admin_required
def feedback_delete(request, feedback_id):
    feedback = get_object_or_404(Feedback, id=feedback_id)
    if request.method == 'POST':
        feedback.delete()
        messages.success(request, 'Feedback message deleted.')
        return redirect('feedback_list')
    return render(request, 'accounts/feedback_delete.html', {'feedback': feedback})




