from django.db import models
from django.contrib.auth.models import User

class SchoolClass(models.Model):
    name = models.CharField(max_length=50)  # e.g., "Math 101"
    grade = models.CharField(max_length=10)  # e.g., "9" or "Grade 9"

    def __str__(self):
        return f"{self.name} - Grade {self.grade}"
    
class Student(models.Model):
    id = models.CharField(max_length=20, primary_key=True)  # Custom student ID (e.g., "S12345")
    name = models.CharField(max_length=100)  # Student’s full name
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE)  # Link to class

    def __str__(self):
        return self.name
    
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('on-time', 'On Time'),
        ('late', 'Late'),
        ('absent', 'Absent'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE)  # Link to student
    date = models.DateField()  # Date of attendance
    check_in_time = models.TimeField(null=True, blank=True)  # Time of check-in (nullable for absent)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)  # Attendance status
    notes = models.TextField(null=True, blank=True)  # Optional notes (e.g., "Medical leave")

    class Meta:
        unique_together = ['student', 'date']  # Ensures one record per student per day

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.status}"
    
class AdminActionLog(models.Model):
    admin = models.ForeignKey(User, on_delete=models.CASCADE)  # Link to Django’s User model
    action = models.TextField()  # Description of the action (e.g., "Updated attendance for S12345")
    timestamp = models.DateTimeField(auto_now_add=True)  # Auto-set to current time

    def __str__(self):
        return f"{self.admin.username} - {self.action} - {self.timestamp}"
