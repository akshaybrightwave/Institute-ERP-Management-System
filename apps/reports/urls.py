from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('students/', views.student_report, name='student_report'),
    path('batches/', views.batch_report, name='batch_report'),
    path('teachers/', views.teacher_report, name='teacher_report'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('fees/', views.fee_report, name='fee_report'),
    path('exams/', views.exam_report, name='exam_report'),
    path('certificates/', views.certificate_report, name='certificate_report'),
]
