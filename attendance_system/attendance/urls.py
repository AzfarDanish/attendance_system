from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('students/', views.student_list, name='student_list'),
    path('students/add/', views.student_add, name='student_add'),
    path('students/edit/<str:student_id>/', views.student_edit, name='student_edit'),
    path('students/delete/<str:student_id>/', views.student_delete, name='student_delete'),
    path('students/import/', views.student_import, name='student_import'),
    path('classes/', views.class_list, name='class_list'),
    path('classes/add/', views.class_add, name='class_add'),
    path('classes/edit/<int:class_id>/', views.class_edit, name='class_edit'),
    path('classes/delete/<int:class_id>/', views.class_delete, name='class_delete'),
    path('attendance-logs/', views.attendance_log_list, name='attendance_log_list'),
    path('qr-check-in/', views.qr_check_in, name='qr_check_in'),
    path('admin-logs/', views.admin_log_list, name='admin_log_list'),
]