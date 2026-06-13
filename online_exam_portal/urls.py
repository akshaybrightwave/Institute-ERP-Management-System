from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

from apps.accounts import views as accounts_views
from apps.exams import views as exam_views
from apps.students import views as student_views
from apps.teachers import views as teacher_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', accounts_views.home, name='home'),
    path('contact/', accounts_views.contact_view, name='contact'),
    path('signup_admin/', accounts_views.signup_admin, name='signup_admin'),
    path('signup_teacher/', accounts_views.signup_teacher, name='signup_teacher'),
    path('signup_student/', accounts_views.signup_student, name='signup_student'),
    path('login/', accounts_views.user_login, name='login'),
    path('logout/', accounts_views.user_logout, name='logout'),

    # Admin Panel urls
    path('admin_dashboard/', accounts_views.admin_dashboard, name='admin_dashboard'),    
    path('admin_users/', accounts_views.user_list, name='user_list'),
    path('admin_users_add/', accounts_views.user_add, name='user_add'),
    path('admin_users/edit/<int:user_id>/', accounts_views.user_edit, name='user_edit'),
    path('admin_users/delete/<int:user_id>/', accounts_views.user_delete, name='user_delete'),

    # Admin Feedback Inbox
    path('admin_feedback/', accounts_views.feedback_list, name='feedback_list'),
    path('admin_feedback/<int:feedback_id>/', accounts_views.feedback_detail, name='feedback_detail'),
    path('admin_feedback/<int:feedback_id>/delete/', accounts_views.feedback_delete, name='feedback_delete'),

    # Exam CRUD (shared for Admin + Teacher)
    path('exams/', exam_views.exam_list, name='exam_list'),
    path('exams_add/', exam_views.add_exam, name='add_exam'),
    path('exams/<int:exam_id>/edit/', exam_views.edit_exam, name='edit_exam'),
    path('exams/<int:exam_id>/delete/', exam_views.delete_exam, name='delete_exam'),

    # Question CRUD (shared for Admin + Teacher)
    path('exam_list_dashboard/', exam_views.exam_question_dashboard_view, name='exam_dashboard'),
    path('exams/<int:exam_id>/questions/', exam_views.question_list, name='question_list'),
    path('exams/<int:exam_id>/questions/add/', exam_views.add_question, name='add_question'),
    path('questions/<int:question_id>/edit/', exam_views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', exam_views.delete_question, name='delete_question'),

    # Student exam URLs
    path('student_dashboard/', student_views.student_dashboard, name='student_dashboard'),
    path('student_profile/', student_views.student_profile, name='student_profile'),
    path('student_profile_edit/', student_views.edit_student_profile, name='edit_student_profile'),
    path('student_exams/', student_views.student_exam_list, name='student_exam_list'),
    path('student_exam/<int:exam_id>/attempt/', student_views.attempt_exam, name='attempt_exam'),
    path('student_exam/<int:exam_id>/submit/', student_views.submit_exam, name='submit_exam'),
    path('student_exam_result/<int:attempt_id>/', student_views.student_exam_result, name='student_exam_result'),
    path('student_exam_history/', student_views.student_exam_history, name='student_exam_history'),
    path('student_exam_attempt/delete/<int:attempt_id>/', student_views.delete_student_exam_attempt, 
         name='delete_student_exam_attempt'),
    path('exam/<int:exam_id>/instructions/', student_views.exam_instructions_view, name='exam_instructions'),

    # Teacher Profile + Dashboard
    path('teacher_dashboard/', teacher_views.teacher_dashboard, name='teacher_dashboard'),
    path('edit_profile/', teacher_views.edit_teacher_profile, name='edit_teacher_profile'),
    path('teacher_profile/', teacher_views.teacher_profile, name='teacher_profile'),
    path('profile/delete/', teacher_views.delete_teacher_profile, name='delete_teacher_profile'),
    path('profile/view/', teacher_views.teacher_profile_detail, name='teacher_profile_detail'),

    # Teacher Exam Dashboard (Submissions & Answers only)
    path('teacher/exam_dashboard/', teacher_views.teacher_exam_dashboard, name='teacher_exam_dashboard'),
    path('teacher/exam/<int:exam_id>/submissions/', teacher_views.view_submissions, name='view_submissions'),
    path('teacher/exam/<int:exam_id>/submissions/export/', teacher_views.export_submissions_csv, name='export_submissions_csv'),
    path('teacher/answers/<int:attempt_id>/', teacher_views.view_student_answers, name='view_student_answers'),
    
    
    
    
    
    # URL 1: The page where they type their email address
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html'), name='password_reset'),
        
    # URL 2: The "Success, we sent you an email" page
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'), name='password_reset_done'),
        
    # URL 3: The secure link they click in their email
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
        
    # URL 4: The "Success, your password is changed" page
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
