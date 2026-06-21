from django import forms
from django.contrib.auth.forms import UserCreationForm

from apps.accounts.models import User
from apps.students.models import StudentProfile
from .models import (
    Candidate,
    CandidateNote,
    FollowUp,
    Interview,
    PlacementCompany,
    PlacementDrive,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
)


class HRSignupForm(UserCreationForm):
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
        user.role = 'hr'
        if commit:
            user.save()
        return user


class HRModelFormMixin:
    def apply_control_styles(self):
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class CandidateBasicForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['full_name', 'gender', 'dob', 'mobile', 'email', 'address']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class CandidateProfessionalForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Candidate
        fields = [
            'qualification',
            'experience',
            'current_company',
            'skills',
            'current_salary',
            'expected_salary',
        ]
        widgets = {
            'skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Python, Excel, Communication...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class CandidateRecruitmentForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['applying_position', 'department', 'source', 'assigned_hr', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_hr'].queryset = User.objects.filter(role='hr', is_active=True).order_by('username')
        self.apply_control_styles()


class CandidateDocumentsForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['resume', 'photo', 'certificates']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class CandidateQuickForm(
    CandidateBasicForm,
    CandidateProfessionalForm,
    CandidateRecruitmentForm,
    CandidateDocumentsForm,
):
    class Meta:
        model = Candidate
        fields = [
            'full_name',
            'gender',
            'dob',
            'mobile',
            'email',
            'address',
            'qualification',
            'experience',
            'current_company',
            'skills',
            'current_salary',
            'expected_salary',
            'applying_position',
            'department',
            'source',
            'assigned_hr',
            'status',
            'resume',
            'photo',
            'certificates',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
            'skills': forms.Textarea(attrs={'rows': 3}),
        }


class FollowUpForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['candidate', 'follow_up_date', 'follow_up_time', 'follow_up_type', 'remarks', 'outcome', 'completed']
        widgets = {
            'follow_up_date': forms.DateInput(attrs={'type': 'date'}),
            'follow_up_time': forms.TimeInput(attrs={'type': 'time'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        candidate = kwargs.pop('candidate', None)
        super().__init__(*args, **kwargs)
        self.fields['candidate'].queryset = Candidate.objects.order_by('full_name')
        if candidate:
            self.fields['candidate'].initial = candidate
            self.fields['candidate'].disabled = True
        self.apply_control_styles()


class InterviewForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Interview
        fields = ['candidate', 'interview_type', 'interviewer', 'date', 'time', 'meeting_link', 'venue']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        candidate = kwargs.pop('candidate', None)
        super().__init__(*args, **kwargs)
        self.fields['candidate'].queryset = Candidate.objects.order_by('full_name')
        if candidate:
            self.fields['candidate'].initial = candidate
            self.fields['candidate'].disabled = True
        self.apply_control_styles()


class InterviewFeedbackForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Interview
        fields = [
            'communication',
            'technical_skills',
            'confidence',
            'overall_rating',
            'remarks',
            'decision',
        ]
        widgets = {
            'communication': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'technical_skills': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'confidence': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'overall_rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'remarks': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class CandidateStatusForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = Candidate
        fields = ['status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class CandidateNoteForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = CandidateNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add an internal HR note...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.apply_control_styles()


class PlacementCompanyForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = PlacementCompany
        fields = [
            'name',
            'industry',
            'contact_person',
            'designation',
            'mobile',
            'email',
            'website',
            'address',
            'city',
            'package_offered',
            'logo',
            'notes',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class PlacementDriveForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = PlacementDrive
        fields = ['company', 'job_role', 'drive_date', 'package', 'eligibility_criteria', 'venue', 'remarks', 'status']
        widgets = {
            'drive_date': forms.DateInput(attrs={'type': 'date'}),
            'eligibility_criteria': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = PlacementCompany.objects.order_by('name', '-updated_at')
        if company:
            self.fields['company'].initial = company
            self.fields['company'].disabled = True
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class PlacementAssignmentForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = PlacementStudentAssignment
        fields = [
            'company',
            'drive',
            'student',
            'student_name',
            'course_name',
            'percentage_or_cgpa',
            'skills',
            'interview_status',
            'final_status',
        ]
        widgets = {
            'skills': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        drive = kwargs.pop('drive', None)
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = PlacementCompany.objects.order_by('name', '-updated_at')
        self.fields['drive'].queryset = PlacementDrive.objects.select_related('company').order_by('-drive_date', '-updated_at')
        self.fields['student'].queryset = StudentProfile.objects.select_related('batch', 'batch__course').order_by('full_name')
        if drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
        elif company:
            self.fields['company'].initial = company
            self.fields['drive'].queryset = PlacementDrive.objects.filter(company=company).order_by('-drive_date', '-updated_at')
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class PlacementInterviewForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = PlacementInterview
        fields = ['company', 'drive', 'assignment', 'interview_round', 'date', 'time', 'venue', 'interviewer', 'remarks', 'status']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        assignment = kwargs.pop('assignment', None)
        drive = kwargs.pop('drive', None)
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = PlacementCompany.objects.order_by('name', '-updated_at')
        self.fields['drive'].queryset = PlacementDrive.objects.select_related('company').order_by('-drive_date', '-updated_at')
        self.fields['assignment'].queryset = PlacementStudentAssignment.objects.select_related('student', 'company', 'drive').order_by('-assigned_at')
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['company'].initial = assignment.company
            self.fields['drive'].initial = assignment.drive
        elif drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
            self.fields['assignment'].queryset = PlacementStudentAssignment.objects.filter(drive=drive).order_by('-assigned_at')
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class PlacementOfferForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = PlacementOffer
        fields = ['assignment', 'company', 'offered_package', 'offer_status', 'joining_status', 'joining_date', 'remarks']
        widgets = {
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        assignment = kwargs.pop('assignment', None)
        super().__init__(*args, **kwargs)
        self.fields['assignment'].queryset = PlacementStudentAssignment.objects.select_related('student', 'company', 'drive').order_by('-assigned_at')
        self.fields['company'].queryset = PlacementCompany.objects.order_by('name', '-updated_at')
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['company'].initial = assignment.company
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()
