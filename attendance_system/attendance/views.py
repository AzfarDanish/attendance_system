from django.shortcuts import render, redirect
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Student, Attendance, AdminActionLog, SchoolClass
from datetime import datetime, time
from django.http import JsonResponse
from django.utils import timezone
from .forms import StudentForm, SchoolClassForm
import json
from datetime import timedelta

# Check if the user is staff or superuser
def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

# Dashboard View
@login_required
@user_passes_test(is_staff_or_superuser)
def dashboard(request):
    today = timezone.now().date()
    total_students = Student.objects.count()
    today_check_ins = Attendance.objects.filter(date=today).count()
    late_check_ins = Attendance.objects.filter(date=today, status='late').count()
    total_classes = SchoolClass.objects.count()

    daily_attendance = []
    labels_daily = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        count = Attendance.objects.filter(date=day).count()
        daily_attendance.append(count)
        labels_daily.append(day.strftime('%Y-%m-%d'))

    now = timezone.now()
    last_24_hours = now - timedelta(hours=24)
    labels_hourly = []
    late_data = []
    on_time_data = []
    for hour in range(24):
        start_time = (last_24_hours + timedelta(hours=hour)).replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)
        labels_hourly.append(start_time.strftime('%I %p').lstrip('0'))
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

# Student Management Views
@login_required
@user_passes_test(is_staff_or_superuser)
def student_list(request):
    students = Student.objects.all()
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'students': students,
    }
    return render(request, 'attendance/student_list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def student_add(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student added successfully.')
            return redirect('student_list')
    else:
        form = StudentForm()
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'form': form,
    }
    return render(request, 'attendance/student_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def student_edit(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Student updated successfully.')
            return redirect('student_list')
    else:
        form = StudentForm(instance=student)
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'form': form,
        'student': student,
    }
    return render(request, 'attendance/student_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def student_delete(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    if request.method == 'POST':
        student.delete()
        messages.success(request, 'Student deleted successfully.')
        return redirect('student_list')
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'student': student,
    }
    return render(request, 'attendance/student_confirm_delete.html', context)

# Class Management Views
@login_required
@user_passes_test(is_staff_or_superuser)
def class_list(request):
    classes = SchoolClass.objects.all()
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'classes': classes,
    }
    return render(request, 'attendance/class_list.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def class_add(request):
    if request.method == 'POST':
        form = SchoolClassForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class added successfully.')
            return redirect('class_list')
    else:
        form = SchoolClassForm()
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'form': form,
    }
    return render(request, 'attendance/class_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def class_edit(request, class_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    if request.method == 'POST':
        form = SchoolClassForm(request.POST, instance=school_class)
        if form.is_valid():
            form.save()
            messages.success(request, 'Class updated successfully.')
            return redirect('class_list')
    else:
        form = SchoolClassForm(instance=school_class)
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'form': form,
        'school_class': school_class,
    }
    return render(request, 'attendance/class_form.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def class_delete(request, class_id):
    school_class = get_object_or_404(SchoolClass, id=class_id)
    if request.method == 'POST':
        school_class.delete()
        messages.success(request, 'Class deleted successfully.')
        return redirect('class_list')
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'school_class': school_class,
    }
    return render(request, 'attendance/class_confirm_delete.html', context)

# QR Check-In View (placeholder, to be added later if not present)
@login_required
def qr_check_in(request):
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'attendance/qr_check_in.html', context)

@login_required
@user_passes_test(is_staff_or_superuser)
def attendance_log_list(request):
    attendance_logs = Attendance.objects.all().select_related('student', 'student__school_class')
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'attendance_logs': attendance_logs,
    }
    return render(request, 'attendance/attendance_log_list.html', context)

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
