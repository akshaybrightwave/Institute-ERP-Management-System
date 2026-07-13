from django import forms
from .models import Subject
from apps.courses.models import Course

class SubjectForm(forms.ModelForm):
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(),
        empty_label="Select Course",
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_course'})
    )
    duration_offset = forms.CharField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_duration_offset'}, choices=[('', 'Select duration')])
    )
    subject_code = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Subject Code', 'id': 'id_subject_code'})
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Subject Name', 'id': 'id_name'})
    )
    subject_type = forms.ChoiceField(
        choices=Subject.SUBJECT_TYPE_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='Both'
    )
    theory_max_marks = forms.IntegerField(
        initial=100,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control dark-input', 'placeholder': '100', 'id': 'id_theory_max_marks'})
    )
    theory_min_marks = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Theory Min Marks', 'id': 'id_theory_min_marks'})
    )
    practical_max_marks = forms.IntegerField(
        initial=100,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control dark-input', 'placeholder': '100', 'id': 'id_practical_max_marks'})
    )
    practical_min_marks = forms.IntegerField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Practical Min Marks', 'id': 'id_practical_min_marks'})
    )

    class Meta:
        model = Subject
        fields = [
            'course', 'duration_offset', 'subject_code', 'name',
            'subject_type', 'theory_max_marks', 'theory_min_marks',
            'practical_max_marks', 'practical_min_marks'
        ]

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            if self.user.role == 'center':
                self.fields['course'].queryset = Course.objects.filter(center=self.user.center)
            else:
                self.fields['course'].queryset = Course.objects.all()

        # Ensure the selected duration_offset is validated as a choice
        if self.is_bound:
            val = self.data.get('duration_offset')
            if val:
                self.fields['duration_offset'].widget.choices = [(val, val)]
        elif self.instance and self.instance.pk:
            val = self.instance.duration_offset
            if val:
                self.fields['duration_offset'].widget.choices = [(val, val)]
