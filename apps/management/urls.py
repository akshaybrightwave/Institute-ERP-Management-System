from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.management_super_admin_dashboard, name='management_super_admin_dashboard'),
    path('dashboard/', views.management_dashboard, name='management_dashboard'),

    # Inquiry CRUD
    path('inquiries/', views.inquiry_list, name='inquiry_list'),
    path('inquiries/add/', views.inquiry_add, name='inquiry_add'),
    path('inquiries/<int:pk>/', views.inquiry_detail, name='inquiry_detail'),
    path('inquiries/<int:pk>/edit/', views.inquiry_edit, name='inquiry_edit'),
    path('inquiries/<int:pk>/delete/', views.inquiry_delete, name='inquiry_delete'),
    path('inquiries/<int:pk>/convert/', views.inquiry_convert, name='inquiry_convert'),
    path('inquiries/<int:pk>/update-call-status/', views.update_call_status, name='update_call_status'),

    # Lead CRUD
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/<int:pk>/', views.lead_detail, name='lead_detail'),
    path('leads/<int:pk>/edit/', views.lead_edit, name='lead_edit'),

    # Call Logs
    path('call-logs/', views.call_log_list, name='call_log_list'),
    path('call-logs/add/', views.call_log_add, name='call_log_add'),

    # Follow Ups
    path('followups/', views.followup_list, name='followup_list'),
    path('followups/add/', views.followup_add, name='followup_add'),
    path('followups/<int:pk>/edit/', views.followup_edit, name='followup_edit'),
    path('followups/<int:pk>/complete/', views.followup_complete, name='followup_complete'),

    # Bulk Inquiry Import
    path('import/', views.inquiry_import, name='inquiry_import'),
    path('import/history/', views.import_history, name='import_history'),
    path('import/sample-csv/', views.download_sample_csv, name='download_sample_csv'),
    path('import/sample-excel/', views.download_sample_excel, name='download_sample_excel'),

    # Lead Notes
    path('leads/<int:pk>/notes/', views.lead_notes_list, name='lead_notes_list'),
    path('leads/<int:pk>/notes/add/', views.lead_note_add, name='lead_note_add'),

    # Phase 11.3 Enhancements
    path('activities/', views.activities_list, name='activities_list'),
    path('import/errors/', views.import_errors, name='import_errors'),
    path('leads/assign/', views.lead_assign, name='lead_assign'),
    path('leads/bulk-action/', views.lead_bulk_action, name='lead_bulk_action'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/telecaller/', views.telecaller_report, name='telecaller_report'),

    # Phase 11.2 Counselor Operations
    path('counselor/dashboard/', views.counselor_dashboard, name='counselor_dashboard'),
    path('counselor/leads/', views.counselor_lead_list, name='counselor_lead_list'),
    path('counselor/leads/<int:pk>/', views.counselor_lead_detail, name='counselor_lead_detail'),
    path('counselor/leads/<int:pk>/status/', views.counselor_lead_status_update, name='counselor_lead_status_update'),
    path('counselor/sessions/', views.counselor_session_list, name='counselor_session_list'),
    path('counselor/sessions/add/', views.counselor_session_add, name='counselor_session_add'),
    path('counselor/sessions/<int:pk>/', views.counselor_session_detail, name='counselor_session_detail'),
    path('counselor/followups/', views.counselor_followup_list, name='counselor_followup_list'),
    path('counselor/followups/add/', views.counselor_followup_add, name='counselor_followup_add'),
    path('counselor/followups/<int:pk>/edit/', views.counselor_followup_edit, name='counselor_followup_edit'),
    path('counselor/followups/<int:pk>/complete/', views.counselor_followup_complete, name='counselor_followup_complete'),
    path('counselor/followups/<int:pk>/miss/', views.counselor_followup_miss, name='counselor_followup_miss'),
    path('counselor/notes/add/<int:lead_pk>/', views.counselor_note_add, name='counselor_note_add'),
    path('counselor/reports/', views.counselor_reports_dashboard, name='counselor_reports_dashboard'),
    path('leads/assign-counselor/', views.lead_assign_counselor, name='lead_assign_counselor'),
    path('counselor/visits/', views.counselor_visit_list, name='counselor_visit_list'),
    path('counselor/visits/add/', views.counselor_visit_add, name='counselor_visit_add'),
    path('counselor/visits/<int:pk>/edit/', views.counselor_visit_edit, name='counselor_visit_edit'),

    # Phase 11.5 — Admission Sheet Management
    path('admissions/', views.admission_list, name='admission_list'),
    path('admissions/create/<int:lead_pk>/', views.admission_create, name='admission_create'),
    path('admissions/<int:pk>/', views.admission_detail, name='admission_detail'),
    path('admissions/<int:pk>/edit/', views.admission_edit, name='admission_edit'),
    path('admissions/report/', views.admission_report, name='admission_report'),
]
