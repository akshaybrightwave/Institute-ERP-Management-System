from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('contact/', views.contact_view, name='contact'),
    path('signup_admin/', views.signup_admin, name='signup_admin'),
    path('signup_teacher/', views.signup_teacher, name='signup_teacher'),
    path('signup_student/', views.signup_student, name='signup_student'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

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
