from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.management_dashboard, name='management_dashboard'),

    # Inquiry CRUD
    path('inquiries/', views.inquiry_list, name='inquiry_list'),
    path('inquiries/add/', views.inquiry_add, name='inquiry_add'),
    path('inquiries/<int:pk>/', views.inquiry_detail, name='inquiry_detail'),
    path('inquiries/<int:pk>/edit/', views.inquiry_edit, name='inquiry_edit'),
    path('inquiries/<int:pk>/delete/', views.inquiry_delete, name='inquiry_delete'),
    path('inquiries/<int:pk>/convert/', views.inquiry_convert, name='inquiry_convert'),

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
]
