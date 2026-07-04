from django import forms
from .models import Exam, Option, Question, ExamSchedule


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
            'batches': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
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


class ExamScheduleForm(forms.ModelForm):
    duration = forms.ChoiceField(
        choices=[
            ('', 'Select duration'),
            ('1 Month', '1 Month'),
            ('2 Months', '2 Months'),
            ('3 Months', '3 Months'),
            ('6 Months', '6 Months'),
            ('1 Year', '1 Year'),
            ('2 Years', '2 Years'),
        ],
        widget=forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'})
    )

    class Meta:
        model = ExamSchedule
        fields = ['center', 'course', 'duration', 'exam_center', 'session']
        widgets = {
            'center': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'course': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'exam_center': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'session': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['center'].empty_label = "Select a Center"
        self.fields['course'].empty_label = "Select a Course"
        self.fields['exam_center'].empty_label = "Select Exam Centre"
        self.fields['session'].empty_label = "Select Session"

    # NOTE: StudentProfileForm → apps/students/forms.py
    #       TeacherProfileForm → apps/teachers/forms.py
