from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . import superadmin_views

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact_view, name='contact'),
    path('signup_admin/', views.signup_admin, name='signup_admin'),
    path('signup_teacher/', views.signup_teacher, name='signup_teacher'),
    path('signup_student/', views.signup_student, name='signup_student'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Super Admin Panel
    path('superadmin/', superadmin_views.dashboard, name='superadmin_dashboard'),
    path('superadmin/search/', superadmin_views.global_search, name='superadmin_search'),
    path('superadmin/users/', superadmin_views.users, name='superadmin_users'),
    path('superadmin/users/add/', superadmin_views.user_create, name='superadmin_user_add'),
    path('superadmin/users/<int:user_id>/', superadmin_views.user_detail, name='superadmin_user_detail'),
    path('superadmin/users/<int:user_id>/edit/', superadmin_views.user_edit, name='superadmin_user_edit'),
    path('superadmin/users/<int:user_id>/reset-password/', superadmin_views.user_reset_password, name='superadmin_user_reset_password'),
    path('superadmin/users/<int:user_id>/<str:action>/', superadmin_views.user_action, name='superadmin_user_action'),
    path('superadmin/hr/', superadmin_views.hr_dashboard, name='superadmin_hr'),
    path('superadmin/hr/recruitment/', superadmin_views.hr_recruitment, name='superadmin_hr_recruitment'),
    path('superadmin/hr/placement/', superadmin_views.hr_placement, name='superadmin_hr_placement'),
    path('superadmin/hr/project/', superadmin_views.hr_project, name='superadmin_hr_project'),
    path('superadmin/hr/external/', superadmin_views.hr_external, name='superadmin_hr_external'),
    path('superadmin/hr/candidates/', superadmin_views.hr_candidates, name='superadmin_hr_candidates'),
    path('superadmin/hr/interviews/', superadmin_views.hr_interviews, name='superadmin_hr_interviews'),
    path('superadmin/hr/performance/', superadmin_views.hr_performance, name='superadmin_hr_performance'),
    path('superadmin/hr/reports/', superadmin_views.hr_reports, name='superadmin_hr_reports'),
    path('superadmin/counsellor/', superadmin_views.counsellor_dashboard, name='superadmin_counsellor'),
    path('superadmin/counsellor/leads/', superadmin_views.counsellor_leads, name='superadmin_counsellor_leads'),
    path('superadmin/counsellor/sessions/', superadmin_views.counsellor_sessions, name='superadmin_counsellor_sessions'),
    path('superadmin/counsellor/followups/', superadmin_views.counsellor_followups, name='superadmin_counsellor_followups'),
    path('superadmin/counsellor/followup-analytics/', superadmin_views.counsellor_followup_analytics, name='superadmin_counsellor_followup_analytics'),
    path('superadmin/counsellor/admissions/', superadmin_views.counsellor_admissions, name='superadmin_counsellor_admissions'),
    path('superadmin/counsellor/admission-analytics/', superadmin_views.counsellor_admission_analytics, name='superadmin_counsellor_admission_analytics'),
    path('superadmin/counsellor/performance/', superadmin_views.counsellor_performance, name='superadmin_counsellor_performance'),
    path('superadmin/counsellor/reports/', superadmin_views.counsellor_reports, name='superadmin_counsellor_reports'),
    path('superadmin/telecaller/', superadmin_views.telecaller_dashboard, name='superadmin_telecaller'),
    path('superadmin/telecaller/leads/', superadmin_views.telecaller_leads, name='superadmin_telecaller_leads'),
    path('superadmin/telecaller/calls/', superadmin_views.telecaller_calls, name='superadmin_telecaller_calls'),
    path('superadmin/telecaller/call-analytics/', superadmin_views.telecaller_call_analytics, name='superadmin_telecaller_call_analytics'),
    path('superadmin/telecaller/appointments/', superadmin_views.telecaller_appointments, name='superadmin_telecaller_appointments'),
    path('superadmin/telecaller/appointment-analytics/', superadmin_views.telecaller_appointment_analytics, name='superadmin_telecaller_appointment_analytics'),
    path('superadmin/telecaller/followup-analytics/', superadmin_views.telecaller_followup_analytics, name='superadmin_telecaller_followup_analytics'),
    path('superadmin/telecaller/performance/', superadmin_views.telecaller_performance, name='superadmin_telecaller_performance'),
    path('superadmin/telecaller/reports/', superadmin_views.telecaller_reports, name='superadmin_telecaller_reports'),
    path('superadmin/user-performance/', superadmin_views.user_performance, name='superadmin_user_performance'),
    path('superadmin/reports/', superadmin_views.reports, name='superadmin_reports'),
    path('superadmin/exports/', superadmin_views.exports, name='superadmin_exports'),
    path('superadmin/notifications/', superadmin_views.notifications, name='superadmin_notifications'),
    path('superadmin/activity-logs/', superadmin_views.activity_logs, name='superadmin_activity_logs'),
    path('superadmin/settings/', superadmin_views.settings, name='superadmin_settings'),

    # Admin Panel urls
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),    
    path('admin_users/', views.user_list, name='user_list'),
    path('admin_users_add/', views.user_add, name='user_add'),
    path('admin_users/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    path('admin_users/delete/<int:user_id>/', views.user_delete, name='user_delete'),

    # Admin Feedback Inbox
    path('admin_feedback/', views.feedback_list, name='feedback_list'),
    path('admin_feedback/<int:feedback_id>/', views.feedback_detail, name='feedback_detail'),
    path('admin_feedback/<int:feedback_id>/delete/', views.feedback_delete, name='feedback_delete'),

    # Password Reset Flow
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),
]
