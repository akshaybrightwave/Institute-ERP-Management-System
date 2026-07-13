from django.urls import path
from . import views

urlpatterns = [
    path('', views.subject_list, name='subject_list'),
    path('<int:pk>/edit/', views.subject_update, name='subject_edit'),
    path('<int:pk>/delete/', views.subject_delete, name='subject_delete'),
    path('<int:pk>/restore/', views.subject_restore, name='subject_restore'),
    path('<int:pk>/permanent-delete/', views.subject_permanent_delete, name='subject_permanent_delete'),
    path('api/course/<int:course_id>/', views.get_course_details, name='get_course_details'),
    path('arrange/', views.arrange_subjects, name='arrange_subjects'),
]
