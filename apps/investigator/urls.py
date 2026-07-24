from django.urls import path

from . import views


urlpatterns = [
    path('', views.investigator_dashboard, name='investigator_dashboard'),
    path('recovery-reports/', views.recovery_reports, name='investigator_recovery_reports'),
    path('recovery-reports/add/', views.recovery_report_add, name='investigator_recovery_add'),
    path('case-work-reports/', views.case_work_reports, name='investigator_case_work_reports'),
    path('case-work-reports/add/', views.case_work_report_add, name='investigator_case_work_add'),
    path('student-wise-report/', views.student_wise_report, name='investigator_student_wise_report'),
    path('universal-report/', views.universal_report, name='investigator_universal_report'),
    path('approval-review/', views.approval_review, name='investigator_approval_review'),
    path('master-settings/', views.master_settings, name='investigator_master_settings'),
    path('master-settings/fraud-types/', views.fraud_type_list, name='investigator_fraud_type_list'),
    path('master-settings/fraud-types/<int:pk>/edit/', views.fraud_type_edit, name='investigator_fraud_type_edit'),
    path('master-settings/fraud-types/<int:pk>/toggle/', views.fraud_type_toggle, name='investigator_fraud_type_toggle'),
    path('master-settings/police-stations/', views.police_station_list, name='investigator_police_station_list'),
    path('master-settings/police-stations/<int:pk>/edit/', views.police_station_edit, name='investigator_police_station_edit'),
    path('master-settings/police-stations/<int:pk>/toggle/', views.police_station_toggle, name='investigator_police_station_toggle'),
    path('export-print/', views.export_print, name='investigator_export_print'),
]
