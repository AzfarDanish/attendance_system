from django.contrib import admin
from django.shortcuts import render
from django.urls import path
from django.http import HttpResponseRedirect
from django.contrib import messages
from .models import SchoolClass, Student, Attendance, AdminActionLog
from .forms import StudentCSVImportForm
from .utils import generate_qr_code
import csv
import io
import os
from django.conf import settings

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'school_class', 'qr_code_link')
    list_filter = ('school_class',)
    search_fields = ('id', 'name')
    actions = ['regenerate_qr_codes']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-csv/', self.admin_site.admin_view(self.import_csv), name='attendance_student_import_csv'),
            path('import-csv/preview/', self.admin_site.admin_view(self.preview_import), name='attendance_student_import_preview'),
            path('import-csv/confirm/', self.admin_site.admin_view(self.confirm_import), name='attendance_student_confirm_import'),
        ]
        return custom_urls + urls

    def qr_code_link(self, obj):
        from django.urls import reverse
        from django.utils.html import format_html
        qr_path = f"media/qrcodes/{obj.id}.png"
        return format_html('<a href="/{}" target="_blank">Download QR Code</a>', qr_path)
    qr_code_link.short_description = 'QR Code'

    def regenerate_qr_codes(self, request, queryset):
        regenerated_count = 0
        for student in queryset:
            qr_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes', f'{student.id}.png')
            # Only regenerate if the QR code file is missing
            if not os.path.exists(qr_path):
                try:
                    generate_qr_code(student.id)
                    regenerated_count += 1
                except Exception as e:
                    self.message_user(request, f"Failed to regenerate QR code for {student.id}: {str(e)}", level='error')
        
        if regenerated_count > 0:
            AdminActionLog.objects.create(
                admin=request.user,
                action=f"Regenerated {regenerated_count} missing QR codes."
            )
            self.message_user(request, f"Successfully regenerated {regenerated_count} missing QR codes.", level='success')
        else:
            self.message_user(request, "No missing QR codes needed regeneration.", level='info')

    def import_csv(self, request):
        if request.method == 'POST':
            form = StudentCSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = form.cleaned_data['csv_file']
                try:
                    # Read CSV
                    csv_text = csv_file.read().decode('utf-8')
                    csv_reader = csv.DictReader(io.StringIO(csv_text))
                    
                    # Validate headers
                    expected_headers = {'name', 'class_name'}
                    if not expected_headers.issubset(csv_reader.fieldnames):
                        messages.error(request, "CSV must include 'name' and 'class_name' headers.")
                        return HttpResponseRedirect(request.path)
                    
                    # Process rows
                    valid_rows = []
                    errors = []
                    existing_ids = set(Student.objects.values_list('id', flat=True))
                    next_id = self.get_next_student_id(existing_ids)
                    
                    for row in csv_reader:
                        name = row.get('name', '').strip()
                        class_name = row.get('class_name', '').strip()
                        error = None
                        
                        # Validate row
                        if not name:
                            error = "Missing name."
                        elif not class_name:
                            error = "Missing class_name."
                        else:
                            try:
                                school_class = SchoolClass.objects.get(name=class_name)
                            except SchoolClass.DoesNotExist:
                                error = f"Class '{class_name}' does not exist."
                        
                        if error:
                            errors.append({'row': row, 'error': error})
                            continue
                        
                        # Generate student ID
                        student_id = f"S{next_id:05d}"
                        next_id += 1
                        
                        valid_rows.append({
                            'student_id': student_id,
                            'name': name,
                            'class_name': class_name,
                            'school_class': school_class,
                        })
                    
                    # Store preview data in session
                    request.session['csv_import_preview'] = {
                        'valid_rows': [
                            {
                                'student_id': row['student_id'],
                                'name': row['name'],
                                'class_name': row['class_name'],
                                'school_class_id': row['school_class'].id,  # Store ID for saving
                            } for row in valid_rows
                        ],
                        'errors': errors,
                    }
                    
                    # Log errors
                    if errors:
                        AdminActionLog.objects.create(
                            admin=request.user,
                            action=f"CSV import attempted with {len(errors)} errors."
                        )
                    
                    # Redirect to preview
                    return HttpResponseRedirect('../import-csv/preview/')
                
                except Exception as e:
                    messages.error(request, f"Error processing CSV: {str(e)}")
                    return HttpResponseRedirect(request.path)
        else:
            form = StudentCSVImportForm()
        
        return render(
            request,
            'admin/attendance/student/import_csv.html',
            {'form': form, 'title': 'Import Students from CSV'}
        )

    def preview_import(self, request):
        preview_data = request.session.get('csv_import_preview', {})
        valid_rows = preview_data.get('valid_rows', [])
        errors = preview_data.get('errors', [])
        
        if not valid_rows and not errors:
            messages.error(request, "No preview data available. Please upload a CSV first.")
            return HttpResponseRedirect('../import-csv/')
        
        return render(
            request,
            'admin/attendance/student/import_preview.html',
            {
                'valid_rows': valid_rows,
                'errors': errors,
                'valid_count': len(valid_rows),
                'error_count': len(errors),
                'title': 'Preview Student Import',
            }
        )

    def confirm_import(self, request):
        if request.method == 'POST':
            preview_data = request.session.get('csv_import_preview', {})
            valid_rows = preview_data.get('valid_rows', [])
            
            if not valid_rows:
                messages.error(request, "No valid students to import.")
                return HttpResponseRedirect('../import-csv/')
            
            # Save students and generate QR codes
            imported_count = 0
            qr_code_count = 0
            existing_ids = set(Student.objects.values_list('id', flat=True))
            
            for row in valid_rows:
                student_id = row['student_id']
                # Skip if ID already exists
                if student_id in existing_ids:
                    continue
                
                # Create student
                Student.objects.create(
                    id=student_id,
                    name=row['name'],
                    school_class_id=row['school_class_id'],
                )
                imported_count += 1
                
                # Generate QR code
                try:
                    generate_qr_code(student_id)
                    qr_code_count += 1
                except Exception as e:
                    # Log QR code failure but continue
                    AdminActionLog.objects.create(
                        admin=request.user,
                        action=f"Failed to generate QR code for {student_id}: {str(e)}"
                    )
            
            # Log the import action
            AdminActionLog.objects.create(
                admin=request.user,
                action=f"Imported {imported_count} students and generated {qr_code_count} QR codes via CSV."
            )
            
            # Clear session data
            request.session.pop('csv_import_preview', None)
            
            # Show success message
            messages.success(request, f"Successfully imported {imported_count} students and generated {qr_code_count} QR codes.")
            
            # Redirect to student list
            return HttpResponseRedirect('../../')
        
        # If not POST, redirect to import page
        return HttpResponseRedirect('../import-csv/')

    def get_next_student_id(self, existing_ids):
        max_num = 0
        for id_str in existing_ids:
            if id_str.startswith('S') and id_str[1:].isdigit():
                max_num = max(max_num, int(id_str[1:]))
        return max_num + 1

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'status', 'check_in_time', 'notes')
    list_filter = ('status', 'date', 'student__school_class')
    search_fields = ('student__name', 'student__id')
    date_hierarchy = 'date'

@admin.register(AdminActionLog)
class AdminActionLogAdmin(admin.ModelAdmin):
    list_display = ('admin', 'action', 'timestamp')
    list_filter = ('admin', 'timestamp')
    date_hierarchy = 'timestamp'