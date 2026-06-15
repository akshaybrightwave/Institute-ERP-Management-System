from django import forms
from .models import Certificate
from apps.students.models import StudentProfile


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['student', 'certificate_number', 'issue_date', 'remarks']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CERT-2026-001'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Remarks...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = StudentProfile.objects.all().order_by('full_name')
        from datetime import date
        if not self.initial.get('issue_date'):
            self.initial['issue_date'] = date.today()
