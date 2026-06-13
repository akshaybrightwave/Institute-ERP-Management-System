from django.urls import path
from . import views


urlpatterns = [
    path('', views.center_list, name='center_list'),
    path('add/', views.center_create, name='center_create'),
    path('<int:pk>/edit/', views.center_update, name='center_edit'),
    path('<int:pk>/delete/', views.center_delete, name='center_delete'),
]
