from django.urls import path
from . import views

urlpatterns = [
    path('list/', views.result_list, name='result_list'),
    path('create/', views.result_create, name='result_create'),
    path('view/<int:pk>/', views.result_view, name='result_view'),
    path('edit/<int:pk>/', views.result_edit, name='result_edit'),
    path('delete/<int:pk>/', views.result_delete, name='result_delete'),
    path('student-durations/', views.get_student_duration_choices, name='get_student_duration_choices'),
    path('student-autocomplete/', views.student_results_autocomplete, name='student_results_autocomplete'),
    path('get-subjects/', views.get_subjects_for_duration, name='get_subjects_for_duration'),
]
