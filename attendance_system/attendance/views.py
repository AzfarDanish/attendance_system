from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Student, Attendance, AdminActionLog
from datetime import datetime, time
from django.http import JsonResponse
import json

# QR Code Check-In View
def qr_check_in(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            student = Student.objects.get(id=student_id)
            today = datetime.now().date()
            
            # Check if already checked in
            if Attendance.objects.filter(student=student, date=today).exists():
                return JsonResponse({'status': 'error', 'message': 'Already checked in today'})
            
            # Determine status based on 7:40 AM cutoff
            current_time = datetime.now().time()
            cutoff_time = time(7, 40)
            status = 'on-time' if current_time <= cutoff_time else 'late'
            
            # Record attendance
            Attendance.objects.create(
                student=student,
                date=today,
                check_in_time=current_time,
                status=status
            )
            
            # Log admin action (if scanned by admin)
            if request.user.is_authenticated:
                AdminActionLog.objects.create(
                    admin=request.user,
                    action=f"Recorded QR check-in for {student.name} ({student_id})"
                )
            
            return JsonResponse({'status': 'success', 'message': f'Check-in recorded: {status}'})
        except Student.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid student ID'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return render(request, 'attendance/qr_check_in.html')

# Manual Attendance Entry View (Admin Only)
@login_required
def manual_attendance(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        status = request.POST.get('status')
        notes = request.POST.get('notes')
        date = request.POST.get('date') or datetime.now().date()
        
        try:
            student = Student.objects.get(id=student_id)
            # Check if already checked in
            if Attendance.objects.filter(student=student, date=date).exists():
                messages.error(request, 'Student already has an attendance record for this date.')
            else:
                Attendance.objects.create(
                    student=student,
                    date=date,
                    check_in_time=datetime.now().time() if status != 'absent' else None,
                    status=status,
                    notes=notes
                )
                AdminActionLog.objects.create(
                    admin=request.user,
                    action=f"Manually recorded {status} for {student.name} ({student_id})"
                )
                messages.success(request, 'Attendance recorded successfully.')
        except Student.DoesNotExist:
            messages.error(request, 'Invalid student ID.')
        
        return redirect('manual_attendance')
    
    students = Student.objects.all()
    return render(request, 'attendance/manual_attendance.html', {'students': students})
