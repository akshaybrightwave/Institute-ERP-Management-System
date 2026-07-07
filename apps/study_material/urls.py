from django.urls import path
from . import views

urlpatterns = [
    path('', views.study_material_list, name='study_material_list'),
    path('edit/<int:pk>/', views.study_material_edit, name='study_material_edit'),
    path('delete/<int:pk>/', views.study_material_delete, name='study_material_delete'),
    path('download/<int:pk>/', views.study_material_download, name='study_material_download'),

    # AJAX Cascade
    path('ajax/get-courses/', views.ajax_get_courses, name='ajax_get_courses'),
]
