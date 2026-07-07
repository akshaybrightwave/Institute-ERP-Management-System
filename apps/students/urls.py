from django.urls import path
from . import views

urlpatterns = [
    path('student_dashboard/', views.student_dashboard, name='student_dashboard'),
    path('student_profile/', views.student_profile, name='student_profile'),
    path('student_profile_edit/', views.edit_student_profile, name='edit_student_profile'),
    path('student_exams/', views.student_exam_list, name='student_exam_list'),
    path('student_exam/<int:exam_id>/attempt/', views.attempt_exam, name='attempt_exam'),
    path('student_exam/<int:exam_id>/submit/', views.submit_exam, name='submit_exam'),
    path('student_exam_result/<int:attempt_id>/', views.student_exam_result, name='student_exam_result'),
    path('student_exam_history/', views.student_exam_history, name='student_exam_history'),
    path('student_exam_attempt/delete/<int:attempt_id>/', views.delete_student_exam_attempt, 
         name='delete_student_exam_attempt'),
    path('exam/<int:exam_id>/instructions/', views.exam_instructions_view, name='exam_instructions'),
    path('admission/', views.student_admission_view, name='student_admission'),
    path('details/', views.student_details_view, name='student_details'),
    path('details/search/', views.student_search_autocomplete, name='student_search_autocomplete'),
    path('id_card/', views.student_id_card_view, name='student_id_card'),
    path('pending-list/', views.student_pending_list, name='student_pending_list'),
    path('approved-list/', views.student_approved_list, name='student_approved_list'),
    path('cancel-list/', views.student_cancelled_list, name='student_cancelled_list'),
    path('approve/<int:pk>/', views.student_approve_action, name='student_approve_action'),
    path('cancel/<int:pk>/', views.student_cancel_action, name='student_cancel_action'),
    path('revert-pending/<int:pk>/', views.student_revert_pending_action, name='student_revert_pending_action'),
    path('list-by-center/', views.student_list_by_center, name='student_list_by_center'),
    path('passout-student/', views.passout_student_list, name='passout_student_list'),
]
