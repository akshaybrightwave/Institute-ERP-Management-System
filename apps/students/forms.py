from django import forms
from .models import StudentProfile


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['full_name', 'phone', 'email', 'profile_picture', 'bio']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
        }
