from django.urls import path
from . import views


urlpatterns = [
    path('', views.certificate_list, name='certificate_list'),
    path('create/', views.certificate_create, name='certificate_create'),
    path('<int:pk>/', views.certificate_detail, name='certificate_detail'),

    path('<int:pk>/delete/', views.certificate_delete, name='certificate_delete'),
]
