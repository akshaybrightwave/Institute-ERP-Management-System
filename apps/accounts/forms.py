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
    batch = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label="Batch",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']
        widgets = {
        'username': forms.TextInput(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'}),
        'password1': forms.PasswordInput(attrs={'class': 'form-control'}),
        'password2': forms.PasswordInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        is_admin = kwargs.pop('is_admin', False)
        super().__init__(*args, **kwargs)
        from apps.batches.models import Batch
        self.fields['batch'].queryset = Batch.objects.all()
        if not is_admin:
            self.fields.pop('batch', None)
        elif self.instance and self.instance.pk:
            try:
                from apps.students.models import StudentProfile
                profile = self.instance.studentprofile
                self.fields['batch'].initial = profile.batch
            except (StudentProfile.DoesNotExist, AttributeError):
                pass

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'student'
        if commit:
            user.save()
            from apps.students.models import StudentProfile
            profile, created = StudentProfile.objects.get_or_create(user=user)
            if created:
                profile.full_name = user.username
                profile.email = user.email
            if 'batch' in self.fields:
                profile.batch = self.cleaned_data.get('batch')
            profile.save()
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
