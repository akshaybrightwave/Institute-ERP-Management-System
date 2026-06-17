from django import forms
from .models import Attendance
from apps.students.models import StudentProfile
from apps.batches.models import Batch

class AttendanceForm(forms.ModelForm):
    class Meta:
        model = Attendance
        fields = ['student', 'batch', 'date', 'status']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'batch': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Prepopulate with today's date if not set
        from datetime import date
        if not self.initial.get('date'):
            self.initial['date'] = date.today()
            
        if self.user and self.user.role == 'center':
            center = self.user.center
            self.fields['student'].queryset = StudentProfile.objects.filter(
                batch__course__center=center
            ).order_by('full_name')
            self.fields['batch'].queryset = Batch.objects.filter(
                course__center=center
            ).order_by('name')
        else:
            self.fields['student'].queryset = StudentProfile.objects.all().order_by('full_name')
            self.fields['batch'].queryset = Batch.objects.all().order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        batch = cleaned_data.get('batch')
        date = cleaned_data.get('date')
        status = cleaned_data.get('status')

        if student and batch:
            # Check student belongs to selected batch
            if student.batch != batch:
                raise forms.ValidationError("Selected student does not belong to the selected batch.")
                
            # Check center isolation
            if self.user and self.user.role == 'center':
                center = self.user.center
                if not batch.course or batch.course.center != center:
                    raise forms.ValidationError("Batch does not belong to your assigned center.")
                if not student.batch or student.batch.course.center != center:
                    raise forms.ValidationError("Student does not belong to your assigned center.")

        if student and date:
            existing = Attendance.objects.filter(student=student, date=date)
            if self.instance and self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise forms.ValidationError("An attendance record for this student on this date already exists.")

        return cleaned_data
