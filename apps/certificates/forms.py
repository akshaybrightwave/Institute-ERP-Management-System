from django import forms
from django.utils import timezone
from .models import Certificate
from apps.centers.models import Center
from apps.students.models import StudentAdmission
from apps.academics.models import AcademicSession
from apps.results.models import Result


class CertificateForm(forms.ModelForm):
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        required=True,
        empty_label="Select a Center",
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_center'})
    )
    
    course_duration = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_course_duration'})
    )

    class Meta:
        model = Certificate
        fields = ['student', 'course_duration', 'issue_date', 'examination_conducted_date']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select', 'id': 'id_student'}),
            'issue_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_issue_date'}),
            'examination_conducted_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date', 'id': 'id_examination_conducted_date'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['student'].empty_label = "Select Student"
        self.fields['issue_date'].initial = timezone.localdate()

        # Handle center restriction
        if self.user and self.user.role == 'center':
            user_center = self.user.center
            self.fields['center'].queryset = Center.objects.filter(id=user_center.id)
            self.fields['center'].initial = user_center
            self.fields['center'].empty_label = None
            self.fields['center'].required = False
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

        # Dynamically set course_duration choices if student is pre-selected or submitted
        student_id = None
        if self.is_bound:
            student_id = self.data.get('student')
        elif self.instance and self.instance.pk:
            student_id = self.instance.student.id

        if student_id:
            try:
                student = StudentAdmission.objects.get(id=student_id)
                duration_str = student.course.duration if student.course else ''
                choices = self._parse_duration_choices(duration_str)
                self.fields['course_duration'].choices = [(c, c) for c in choices]
            except StudentAdmission.DoesNotExist:
                pass
        else:
            self.fields['course_duration'].choices = [('', 'Select Student First')]

    def _parse_duration_choices(self, duration_str):
        if not duration_str:
            return []
        parts = duration_str.strip().split()
        if len(parts) < 2:
            return []
        try:
            val = int(parts[0])
        except ValueError:
            return []
        unit = parts[1].rstrip('s')  # Remove plural 's'
        
        choices = []
        for i in range(1, val + 1):
            choices.append(f"{unit} {i}")
        return choices

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        course_duration = cleaned_data.get('course_duration')

        if self.user and self.user.role == 'center':
            cleaned_data['center'] = self.user.center
            if student and student.center != self.user.center:
                raise forms.ValidationError("You can only generate certificates for students in your center.")

        # Find Academic Session
        session = AcademicSession.objects.filter(status=True).first()
        if not session:
            session = AcademicSession.objects.order_by('-id').first()

        if not session:
            raise forms.ValidationError("No academic session is configured in the system.")

        if student and course_duration:
            # Prevent duplicate certificate
            qs = Certificate.objects.filter(student=student, session=session, course_duration=course_duration)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    f"Certificate already exists for student {student.student_name} for '{course_duration}' in session '{session.session_name}'."
                )
                
            # Verify Result exists
            result_qs = Result.objects.filter(student=student, session=session, course_duration=course_duration)
            if not result_qs.exists():
                raise forms.ValidationError(
                    "The selected student's result for the chosen course duration has not been published yet. Please publish the student's result first, then generate the certificate."
                )

        cleaned_data['session'] = session
        return cleaned_data
