from django import forms
from .models import Student, SchoolClass

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['id', 'name', 'school_class']
        widgets = {
            'id': forms.TextInput(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'school_class': forms.Select(attrs={'class': 'form-control'}),
        }

class SchoolClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ['name', 'grade']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'grade': forms.TextInput(attrs={'class': 'form-control'}),
        }

class StudentCSVImportForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV File")

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV.")
        return csv_file
    