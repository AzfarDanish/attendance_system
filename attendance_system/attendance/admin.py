from django.contrib import admin
from .models import SchoolClass, Student, Attendance, AdminActionLog

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade')

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'school_class')
    list_filter = ('school_class',)
    search_fields = ('id', 'name')

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
    