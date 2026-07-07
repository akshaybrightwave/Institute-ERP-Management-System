from django.urls import path
from . import views

urlpatterns = [
    # Exam CRUD (shared for Admin + Teacher)
    path('exams/', views.exam_list, name='exam_list'),
    path('exams_add/', views.add_exam, name='add_exam'),
    path('ajax/get-course-durations/', views.ajax_get_course_durations, name='ajax_get_course_durations'),
    path('exams/<int:exam_id>/', views.exam_detail, name='exam_detail'),
    path('exams/<int:exam_id>/edit/', views.edit_exam, name='edit_exam'),
    path('exams/<int:exam_id>/delete/', views.delete_exam, name='delete_exam'),

    # Question CRUD (shared for Admin + Teacher)
    path('exam_list_dashboard/', views.exam_question_dashboard_view, name='exam_dashboard'),
    path('exams/<int:exam_id>/questions/', views.question_list, name='question_list'),
    path('exams/<int:exam_id>/questions/add/', views.add_question, name='add_question'),
    path('questions/<int:question_id>/edit/', views.edit_question, name='edit_question'),
    path('questions/<int:question_id>/delete/', views.delete_question, name='delete_question'),

    # Option CRUD (shared for Admin + Teacher)
    path('questions/<int:question_id>/options/add/', views.add_option, name='add_option'),
    path('options/<int:option_id>/edit/', views.edit_option, name='edit_option'),
    path('options/<int:option_id>/delete/', views.delete_option, name='delete_option'),

    # Center Exam Monitoring and Submissions (Phase 10.9)
    path('exams/<int:exam_id>/results/', views.center_exam_results, name='center_exam_results'),
    path('exams/<int:exam_id>/results/export/', views.export_exam_results_csv, name='export_exam_results_csv'),
    path('attempts/', views.center_attempts_list, name='center_attempts_list'),
    path('attempts/<int:attempt_id>/', views.center_attempt_detail, name='center_attempt_detail'),
    path('reports/exams/student-performance/export/', views.export_student_performance_csv, name='export_student_performance_csv'),
    path('reports/exams/batch-performance/export/', views.export_batch_performance_csv, name='export_batch_performance_csv'),
    path('schedules/', views.exam_schedule_list, name='exam_schedule_list'),
    path('schedules/<int:pk>/edit/', views.exam_schedule_edit, name='exam_schedule_edit'),
    path('schedules/<int:pk>/delete/', views.exam_schedule_delete, name='exam_schedule_delete'),
]
