from django.urls import path
from . import views


urlpatterns = [
    path('timetable/', views.timetable_list, name='timetable_list'),
    path('timetable/<int:pk>/edit/', views.timetable_edit, name='timetable_edit'),
    path('timetable/<int:pk>/delete/', views.timetable_delete, name='timetable_delete'),

    path('session/', views.session_list, name='session_list'),
    path('session/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('session/<int:pk>/delete/', views.session_delete, name='session_delete'),
    path('session/<int:pk>/toggle-status/', views.session_toggle_status, name='session_toggle_status'),

    path('occupation/', views.occupation_list, name='occupation_list'),
    path('occupation/<int:pk>/edit/', views.occupation_edit, name='occupation_edit'),
    path('occupation/<int:pk>/delete/', views.occupation_delete, name='occupation_delete'),
]
