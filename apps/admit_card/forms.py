from django import forms
from .models import AdmitCard
from apps.centers.models import Center
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession


class AdmitCardForm(forms.ModelForm):
    # Field to select center (which filters the students dropdown)
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        required=True,
        empty_label="Select a Center",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_center'})
    )
    
    # Read-only fields populated via AJAX
    course = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'id_course'})
    )
    
    course_duration = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly', 'id': 'id_course_duration'})
    )

    class Meta:
        model = AdmitCard
        fields = ['student', 'session', 'roll_number', 'status']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select', 'id': 'id_student'}),
            'session': forms.Select(attrs={'class': 'form-select'}),
            'roll_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Roll No.'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['session'].empty_label = "Select Session"
        self.fields['student'].empty_label = "Select Student"
        
        # Restrict center choice if the user is a center manager
        if self.user and self.user.role == 'center':
            user_center = self.user.center
            self.fields['center'].queryset = Center.objects.filter(id=user_center.id)
            self.fields['center'].initial = user_center
            self.fields['center'].widget.attrs.update({'disabled': 'disabled'})
            self.fields['student'].queryset = StudentAdmission.objects.filter(
                center=user_center,
                status='Approved'
            ).order_by('student_name')
        else:
            self.fields['center'].queryset = Center.objects.all().order_by('name')
            self.fields['student'].queryset = StudentAdmission.objects.filter(
                status='Approved'
            ).order_by('student_name')

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        session = cleaned_data.get('session')
        roll_number = cleaned_data.get('roll_number')

        # Center users can only generate admit cards for their own students
        if self.user and self.user.role == 'center' and student:
            if student.center != self.user.center:
                raise forms.ValidationError("You can only generate admit cards for students in your center.")

        # Prevent duplicate Admit Cards for the same student + session
        if student and session:
            qs = AdmitCard.objects.filter(student=student, session=session)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Student {student.student_name} already has an Admit Card generated for the session '{session.session_name}'."
                )

        # Prevent duplicate Roll Numbers within the same session
        if roll_number and session:
            qs = AdmitCard.objects.filter(roll_number=roll_number, session=session)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Roll number '{roll_number}' is already assigned to a student in the session '{session.session_name}'."
                )

        return cleaned_data


