from django import forms 
from django.contrib.auth.forms import UserCreationForm
from .models import Feedback, User

class AdminSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
        'username': forms.TextInput(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'}),
        'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
        'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'admin'
        if commit:
            user.save()
        return user

# class TeacherSignupForm(UserCreationForm):
#     class Meta:
#         model = User
#         fields = ['username', 'email', 'password1', 'password2']

#     def save(self, commit=True):
#         user = super().save(commit=False)
#         user.role = 'teacher'
#         if commit:
#             user.save()
#         return user



class TeacherSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
        'username': forms.TextInput(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'}),
        'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
        'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'teacher'
        if commit:
            user.save()
        return user




class StudentSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
        'username': forms.TextInput(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'}),
        'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
        'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }
        

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
        return user
    


# Feedback form
class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'subject': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }
