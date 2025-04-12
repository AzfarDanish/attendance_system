from django.urls import path
from . import views

urlpatterns = [
    path('qr-check-in/', views.qr_check_in, name='qr_check_in'),
    path('manual-attendance/', views.manual_attendance, name='manual_attendance'),
]
