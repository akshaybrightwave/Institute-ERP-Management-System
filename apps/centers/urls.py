from django.urls import path
from . import views


urlpatterns = [
    path('', views.center_list, name='center_list'),
    path('add/', views.center_create, name='center_create'),
    path('<int:pk>/edit/', views.center_update, name='center_edit'),
    path('<int:pk>/delete/', views.center_delete, name='center_delete'),
    path('dashboard/', views.center_dashboard, name='center_dashboard'),
    path('assign-courses/', views.assign_courses, name='assign_courses'),
    path('api/center-courses/<int:center_id>/', views.api_center_courses, name='api_center_courses'),
    path('api/assign-course-toggle/', views.api_assign_course_toggle, name='api_assign_course_toggle'),
    path('pending/', views.pending_centers, name='pending_centers'),
    path('info-list/', views.center_info_list, name='center_info_list'),
    path('<int:pk>/load-wallet/', views.load_wallet, name='center_load_wallet'),
    path('<int:pk>/profile/', views.center_profile, name='center_profile'),
    path('deleted/', views.deleted_centers, name='deleted_centers'),
    path('<int:pk>/restore/', views.restore_center, name='restore_center'),
    
    # Center Certificates
    path('certificates/', views.center_certificate_list, name='center_certificate_list'),
    path('certificates/add/', views.center_certificate_create, name='center_certificate_create'),
    path('certificates/<int:pk>/', views.center_certificate_detail, name='center_certificate_detail'),
    path('certificates/<int:pk>/edit/', views.center_certificate_update, name='center_certificate_edit'),
    path('certificates/<int:pk>/delete/', views.center_certificate_delete, name='center_certificate_delete'),
]
