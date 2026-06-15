from django import forms
from .models import FeePayment
from apps.students.models import StudentProfile


class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        fields = ['student', 'amount', 'payment_date', 'payment_method', 'reference_number', 'remarks']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['student'].queryset = StudentProfile.objects.all().order_by('full_name')
        # Prepopulate with today's date if not set
        from datetime import date
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = date.today()
