from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Student, Attendance, AdminActionLog, SchoolClass
from datetime import datetime, time
from django.http import JsonResponse
from django.utils import timezone
import json
from datetime import timedelta

# Check if the user is staff or superuser
def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard(request):
    # Calculate metrics for the cards
    today = timezone.now().date()
    total_students = Student.objects.count()
    today_check_ins = Attendance.objects.filter(date=today).count()
    late_check_ins = Attendance.objects.filter(date=today, status='late').count()
    total_classes = SchoolClass.objects.count()

    # Daily Attendance Trend (last 7 days)
    daily_attendance = []
    labels_daily = []
    for i in range(6, -1, -1):  # Last 7 days, including today
        day = today - timedelta(days=i)
        count = Attendance.objects.filter(date=day).count()
        daily_attendance.append(count)
        labels_daily.append(day.strftime('%Y-%m-%d'))

    # Late vs On-Time Check-Ins (last 24 hours)
    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)
    labels_hourly = []
    late_data = []
    on_time_data = []

    # Group by hour (last 24 hours)
    for hour in range(24):
        start_time = (last_24_hours + timedelta(hours=hour)).replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        labels_hourly.append(start_time.strftime('%I %p').lstrip('0'))  # e.g., "8 AM"
        late_count = Attendance.objects.filter(
            check_in_time__gte=start_time.time(),
            check_in_time__lt=end_time.time(),
            date=start_time.date(),
            status='late'
        ).count()
        on_time_count = Attendance.objects.filter(
            check_in_time__gte=start_time.time(),
            check_in_time__lt=end_time.time(),
            date=start_time.date(),
            status='on-time'
        ).count()
        # Adjust for cross-day boundaries
        if start_time.date() != end_time.date():
            late_count += Attendance.objects.filter(
                check_in_time__gte=start_time.time(),
                date=start_time.date(),
                status='late'
            ).count()
            late_count += Attendance.objects.filter(
                check_in_time__lt=end_time.time(),
                date=end_time.date(),
                status='late'
            ).count()
            on_time_count += Attendance.objects.filter(
                check_in_time__gte=start_time.time(),
                date=start_time.date(),
                status='on-time'
            ).count()
            on_time_count += Attendance.objects.filter(
                check_in_time__lt=end_time.time(),
                date=end_time.date(),
                status='on-time'
            ).count()
        late_data.append(late_count)
        on_time_data.append(on_time_count)

    # Debug prints to check data
    print("Daily Labels:", labels_daily)
    print("Daily Data:", daily_attendance)
    print("Hourly Labels:", labels_hourly)
    print("Late Data:", late_data)
    print("On-Time Data:", on_time_data)

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'total_students': total_students,
        'today_check_ins': today_check_ins,
        'late_check_ins': late_check_ins,
        'total_classes': total_classes,
        'daily_attendance_data': daily_attendance,
        'daily_attendance_labels': labels_daily,
        'hourly_late_data': late_data,
        'hourly_on_time_data': on_time_data,
        'hourly_labels': labels_hourly,
    }
    return render(request, 'attendance/dashboard.html', context)

def qr_check_in(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            student_id = data.get('student_id')
            student = Student.objects.get(id=student_id)
            today = timezone.now().date()
            
            # Check if already checked in
            existing_check_in = Attendance.objects.filter(student=student, date=today).first()
            if existing_check_in:
                return JsonResponse({'status': 'error', 'message': 'Already checked in today.'})
            
            # Determine status based on time
            current_time = timezone.now().time()
            on_time_threshold = datetime.strptime('08:00:00', '%H:%M:%S').time()
            status = 'on-time' if current_time <= on_time_threshold else 'late'
            
            # Record attendance
            Attendance.objects.create(
                student=student,
                date=today,
                status=status,
                check_in_time=current_time
            )
            
            return JsonResponse({'status': 'success', 'message': f'Check-in recorded: {status}'})
        except Student.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return render(request, 'attendance/qr_check_in.html', {'csrf_token': request.COOKIES.get('csrftoken', '')})

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
