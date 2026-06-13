from django import forms
from .models import Batch


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['course', 'teacher', 'name', 'start_date', 'end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }
