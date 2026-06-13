from django.urls import path
from . import views

urlpatterns = [
    # Teacher Profile + Dashboard
    path('teacher_dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('edit_profile/', views.edit_teacher_profile, name='edit_teacher_profile'),
    path('teacher_profile/', views.teacher_profile, name='teacher_profile'),
    path('profile/delete/', views.delete_teacher_profile, name='delete_teacher_profile'),
    path('profile/view/', views.teacher_profile_detail, name='teacher_profile_detail'),

    # Teacher Exam Dashboard (Submissions & Answers only)
    path('teacher/exam_dashboard/', views.teacher_exam_dashboard, name='teacher_exam_dashboard'),
    path('teacher/exam/<int:exam_id>/submissions/', views.view_submissions, name='view_submissions'),
    path('teacher/exam/<int:exam_id>/submissions/export/', views.export_submissions_csv, name='export_submissions_csv'),
    path('teacher/answers/<int:attempt_id>/', views.view_student_answers, name='view_student_answers'),
    
    # Teacher Batch details
    path('batches/<int:pk>/', views.teacher_batch_detail, name='teacher_batch_detail'),
]
