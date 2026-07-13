from django.urls import path
from . import views


urlpatterns = [
    path('', views.course_list, name='course_list'),
    path('add/', views.course_create, name='course_create'),
    path('<int:pk>/edit/', views.course_update, name='course_edit'),
    path('<int:pk>/delete/', views.course_delete, name='course_delete'),
    path('<int:pk>/restore/', views.course_restore, name='course_restore'),
    path('<int:pk>/permanent-delete/', views.course_permanent_delete, name='course_permanent_delete'),
]
