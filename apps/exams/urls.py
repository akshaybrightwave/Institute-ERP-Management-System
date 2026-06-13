from django.urls import path
from . import views

urlpatterns = [
    # Exam CRUD (shared for Admin + Teacher)
    path('exams/', views.exam_list, name='exam_list'),
    path('exams_add/', views.add_exam, name='add_exam'),
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
]
