from django import forms
from .models import Exam, Option, Question


class ExamForm(forms.ModelForm):
    date = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    end_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Exam
        fields = [
            'title', 'description', 'date', 'end_date', 'total_marks', 'duration_minutes',
            'pass_percentage', 'negative_marks', 'allow_retake', 'is_published', 'batches',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'total_marks': forms.NumberInput(attrs={'class': 'form-control'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'pass_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
            'negative_marks': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.25', 'min': 0}),
            'allow_retake': forms.CheckboxInput(attrs={'class': 'form-check-input ms-2'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input ms-2'}),
            'batches': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.role == 'teacher':
            from apps.batches.models import Batch
            from apps.teachers.models import TeacherProfile
            profile = TeacherProfile.objects.filter(user=user).first()
            if profile:
                self.fields['batches'].queryset = Batch.objects.filter(teacher=profile)
            else:
                self.fields['batches'].queryset = Batch.objects.none()


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'marks']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter option text'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # NOTE: StudentProfileForm → apps/students/forms.py
    #       TeacherProfileForm → apps/teachers/forms.py
