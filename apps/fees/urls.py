from django.urls import path
from . import views


urlpatterns = [
    path('', views.fees_list, name='fees_list'),
    path('search-fees-payment/', views.search_fee_payment, name='search_fees_payment'),
    path('payments/add/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/edit/', views.payment_update, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    path('payments/<int:pk>/receipt/', views.payment_receipt, name='payment_receipt'),
    path('ajax/student-autocomplete/', views.student_fee_autocomplete, name='fee_student_autocomplete'),
    path('ajax/student-fee-summary/', views.student_fee_summary_ajax, name='fee_student_summary'),
]
