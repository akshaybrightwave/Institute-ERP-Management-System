from django.urls import path
from . import views

urlpatterns = [
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student_profile/', views.student_profile, name='student_profile'),
    path('student_profile_edit/', views.edit_student_profile, name='edit_student_profile'),
    path('student_exams/', views.student_exam_list, name='student_exam_list'),
    path('student_exam/<int:exam_id>/attempt/', views.attempt_exam, name='attempt_exam'),
    path('student_exam/<int:exam_id>/submit/', views.submit_exam, name='submit_exam'),
    path('student_exam_result/<int:attempt_id>/', views.student_exam_result, name='student_exam_result'),
    path('student_exam_history/', views.student_exam_history, name='student_exam_history'),
    path('student_exam_attempt/delete/<int:attempt_id>/', views.delete_student_exam_attempt, 
         name='delete_student_exam_attempt'),
    path('exam/<int:exam_id>/instructions/', views.exam_instructions_view, name='exam_instructions'),
]
