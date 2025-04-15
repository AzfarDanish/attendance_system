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
import csv
from io import TextIOWrapper
import qrcode
import base64
from io import BytesIO
from django.db.models import Q

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
    # Get search and filter parameters
    search_query = request.GET.get('search', '')
    class_filter = request.GET.get('class', '')

    # Start with all students
    students = Student.objects.all()

    # Apply search filter (by name or ID)
    if search_query:
        students = students.filter(
            Q (name__icontains=search_query) | Q(id__icontains=search_query)
        )

    # Apply class filter
    if class_filter:
        students = students.filter(school_class__id=class_filter)

    # Get all classes for the filter dropdown
    classes = SchoolClass.objects.all()

    # Generate QR codes for each student
    students_with_qr = []
    for student in students:
        qr = qrcode.QRCode(version=1, box_size=10, border=1)
        qr.add_data(student.id)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
        students_with_qr.append({
            'id': student.id,
            'name': student.name,
            'school_class': student.school_class,
            'qr_code': img_str,
        })

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'students': students_with_qr,
        'classes': classes,
        'search_query': search_query,
        'class_filter': class_filter,
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

# Attendance Logs View
@login_required
@user_passes_test(is_staff_or_superuser)
def attendance_log_list(request):
    attendance_logs = Attendance.objects.all().select_related('student', 'student__school_class')
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'attendance_logs': attendance_logs,
    }
    return render(request, 'attendance/attendance_log_list.html', context)

# QR Check-In View
@login_required
def qr_check_in(request):
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(id=student_id)
            # Check if the student has already checked in today
            today = timezone.now().date()
            existing_check_in = Attendance.objects.filter(student=student, date=today).first()
            if existing_check_in:
                messages.error(request, f'{student.name} has already checked in today.')
            else:
                # Determine status based on time (e.g., late if after 8 AM)
                now = timezone.now()
                check_in_time = now.time()
                late_threshold = timezone.datetime.strptime('08:00', '%H:%M').time()
                status = 'late' if check_in_time > late_threshold else 'on-time'
                # Log attendance
                Attendance.objects.create(
                    student=student,
                    date=today,
                    check_in_time=check_in_time,
                    status=status
                )
                messages.success(request, f'Check-in successful for {student.name} at {check_in_time}. Status: {status}.')
        except Student.DoesNotExist:
            messages.error(request, 'Student not found. Please check the ID.')
        context = {
            'admin_name': request.user.get_full_name() or request.user.username,
        }
        return render(request, 'attendance/qr_check_in.html', context)

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'attendance/qr_check_in.html', context)

def generate_student_id(existing_ids):
    last_student = Student.objects.order_by('-id').first()
    last_id_number = 0
    if last_student:
        last_id_number = max(last_id_number, int(last_student.id.replace('S', '')))
    for student_id in existing_ids:
        id_number = int(student_id.replace('S', ''))
        last_id_number = max(last_id_number, id_number)
    new_id = last_id_number + 1
    return f'S{new_id:05d}'

# Student Import View
@login_required
@user_passes_test(is_staff_or_superuser)
def student_import(request):
    if request.method == 'POST':
        if 'preview' in request.POST:
            csv_file = request.FILES.get('csv_file')
            if not csv_file:
                messages.error(request, 'No file uploaded. Please select a CSV file.')
                return redirect('student_import')
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Invalid file format. Please upload a CSV file.')
                return redirect('student_import')

            try:
                text_io = TextIOWrapper(csv_file.file, encoding='utf-8')
                reader = csv.DictReader(text_io)
                required_columns = {'name', 'class_name'}
                if not all(col in reader.fieldnames for col in required_columns):
                    messages.error(request, 'CSV file must contain "name" and "class_name" columns.')
                    return redirect('student_import')

                preview_data = []
                existing_ids = set()
                for row in reader:
                    student_name = row['name'].strip()
                    class_name = row['class_name'].strip()
                    error = None

                    if not student_name:
                        error = "Student name cannot be empty."
                    if not class_name:
                        error = "Class name cannot be empty."
                    else:
                        school_class = SchoolClass.objects.filter(name=class_name).first()
                        if not school_class:
                            error = f"School class '{class_name}' does not exist."

                    student_id = generate_student_id(existing_ids)
                    existing_ids.add(student_id)

                    preview_data.append({
                        'id': student_id,
                        'name': student_name,
                        'class_name': class_name,
                        'error': error,
                    })

                context = {
                    'admin_name': request.user.get_full_name() or request.user.username,
                    'preview_data': preview_data,
                }
                return render(request, 'attendance/student_import.html', context)

            except Exception as e:
                messages.error(request, f'Error processing CSV file: {str(e)}')
                return redirect('student_import')

        elif 'confirm' in request.POST:
            preview_data_json = request.POST.get('preview_data')
            if not preview_data_json:
                messages.error(request, 'No preview data found. Please upload the CSV file again.')
                return redirect('student_import')

            try:
                preview_data = json.loads(preview_data_json)
                imported = 0
                errors = []

                for index, row in enumerate(preview_data, start=2):
                    if row.get('error'):
                        errors.append(f"Row {index}: {row['error']}")
                        continue

                    try:
                        school_class = SchoolClass.objects.get(name=row['class_name'])
                        Student.objects.create(
                            id=row['id'],
                            name=row['name'],
                            school_class=school_class,
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Row {index}: {str(e)}")

                if imported > 0:
                    messages.success(request, f'Successfully imported {imported} students.')
                if errors:
                    for error in errors:
                        messages.error(request, error)
                return redirect('student_list')

            except Exception as e:
                messages.error(request, f'Error during import: {str(e)}')
                return redirect('student_import')

    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
    }
    return render(request, 'attendance/student_import.html', context)

# Admin Logs View
@login_required
@user_passes_test(is_staff_or_superuser)
def admin_log_list(request):
    admin_logs = AdminActionLog.objects.all().select_related('admin')
    context = {
        'admin_name': request.user.get_full_name() or request.user.username,
        'admin_logs': admin_logs,
    }
    return render(request, 'attendance/admin_log_list.html', context)

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
