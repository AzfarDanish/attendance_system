from django import forms

class StudentCSVImportForm(forms.Form):
    csv_file = forms.FileField(label="Upload CSV File")

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if not csv_file.name.endswith('.csv'):
            raise forms.ValidationError("File must be a CSV.")
        return csv_file
    