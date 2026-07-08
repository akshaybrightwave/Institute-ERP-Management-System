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
]
