from django.urls import path
from . import views


urlpatterns = [
    path('', views.batch_list, name='batch_list'),
    path('add/', views.batch_create, name='batch_create'),
    path('<int:pk>/edit/', views.batch_update, name='batch_edit'),
    path('<int:pk>/delete/', views.batch_delete, name='batch_delete'),
]
