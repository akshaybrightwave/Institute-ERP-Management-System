from django.urls import path
from . import views

urlpatterns = [
    path('', views.admit_card_list, name='admit_card_list'),
    path('generate/', views.admit_card_create, name='admit_card_create'),
    path('view/<int:pk>/', views.admit_card_view, name='admit_card_view'),
    path('delete/<int:pk>/', views.admit_card_delete, name='admit_card_delete'),
    path('get-student-details/', views.get_student_details, name='get_student_details'),
    path('student-autocomplete/', views.student_admit_card_autocomplete, name='student_admit_card_autocomplete'),
]
