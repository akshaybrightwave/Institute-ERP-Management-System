from django.urls import path
from . import views


urlpatterns = [
    path('', views.fees_list, name='fees_list'),
    path('payments/add/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
]
