from django.urls import path
from . import views


urlpatterns = [
    path('', views.attendance_list, name='attendance_list'),
    path('student-attendance/', views.student_attendance, name='student_attendance'),
    path('by-date/', views.attendance_by_date, name='attendance_by_date'),
    path('mark/<int:batch_id>/', views.mark_attendance, name='mark_attendance'),
    path('create/', views.attendance_create, name='attendance_create'),
    path('<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
]
