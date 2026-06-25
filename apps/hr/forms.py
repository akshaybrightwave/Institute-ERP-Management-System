from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError

from apps.accounts.models import User
from apps.students.models import StudentProfile
from .models import (
    Candidate,
    CandidateNote,
    ExternalAttendanceLog,
    ExternalEmployee,
    FollowUp,
    Interview,
    PlacementCompany,
    PlacementDrive,
    PlacementInterview,
    PlacementOffer,
    PlacementStudentAssignment,
    ProjectAllocation,
    ProjectCompany,
    ProjectDrive,
    ProjectEmployeeAssignment,
    ProjectInterview,
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

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('An account with this username already exists.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'hr'
        if commit:
            try:
                user.save()
            except IntegrityError as exc:
                if 'username' in str(exc).lower():
                    self.add_error('username', 'An account with this username already exists.')
                elif 'email' in str(exc).lower():
                    self.add_error('email', 'An account with this email already exists.')
                else:
                    self.add_error(None, 'Unable to create this HR account. Please check the details and try again.')
                raise forms.ValidationError(self.errors)
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
        fields = ['resume', 'photo']

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


class ExternalEmployeeForm(HRModelFormMixin, forms.ModelForm):
    personal_fields = ['full_name', 'mobile', 'email', 'dob', 'gender', 'address', 'emergency_contact']
    employment_fields = ['employee_id', 'user', 'branch', 'department', 'designation', 'joining_date', 'employment_type', 'reporting_manager', 'status']
    document_fields = ['aadhaar', 'pan', 'resume']

    class Meta:
        model = ExternalEmployee
        fields = [
            'full_name',
            'dob',
            'gender',
            'email',
            'mobile',
            'address',
            'emergency_contact',
            'employee_id',
            'user',
            'branch',
            'department',
            'designation',
            'joining_date',
            'employment_type',
            'reporting_manager',
            'status',
            'aadhaar',
            'pan',
            'resume',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        branch = kwargs.pop('branch', None)
        current_user = kwargs.pop('current_user', None)
        allow_all_users = kwargs.pop('allow_all_users', False)
        super().__init__(*args, **kwargs)
        if branch:
            self.fields['branch'].initial = branch
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('username')
        if current_user and not allow_all_users:
            self.fields['user'].queryset = User.objects.filter(pk=current_user.pk)
            self.fields['user'].initial = current_user
            self.fields['user'].disabled = True
        self.fields['user'].required = False
        self.fields['user'].label = 'Login User'
        self.apply_control_styles()


class ExternalAttendanceForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ExternalAttendanceLog
        fields = ['employee', 'date', 'check_in', 'check_out', 'working_hours', 'status', 'location_ip', 'last_activity', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'check_in': forms.TimeInput(attrs={'type': 'time'}),
            'check_out': forms.TimeInput(attrs={'type': 'time'}),
            'last_activity': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        branch = kwargs.pop('branch', None)
        employee_queryset = kwargs.pop('employee_queryset', None)
        super().__init__(*args, **kwargs)
        self.fields['employee'].queryset = ExternalEmployee.objects.order_by('full_name')
        if branch:
            self.fields['employee'].queryset = self.fields['employee'].queryset.filter(branch=branch)
        if employee_queryset is not None:
            self.fields['employee'].queryset = employee_queryset
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
            'package_offered': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
            'project_value': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
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
            'package_offered': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
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
            'package': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA, Negotiable'}),
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
        self.fields['student_name'].label = 'Employee Name'
        self.fields['course_name'].label = 'Designation'
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
            'offered_package': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
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


class ProjectCompanyForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectCompany
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
            'project_value',
            'logo',
            'notes',
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'package_offered': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
            'project_value': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class ProjectDriveForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectDrive
        fields = ['company', 'project_name', 'role_required', 'drive_date', 'project_value', 'eligibility_criteria', 'venue', 'remarks', 'status']
        widgets = {
            'drive_date': forms.DateInput(attrs={'type': 'date'}),
            'eligibility_criteria': forms.Textarea(attrs={'rows': 3}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'project_value': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        self.fields['company'].queryset = ProjectCompany.objects.order_by('name', '-updated_at')
        if company:
            self.fields['company'].initial = company
            self.fields['company'].disabled = True
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class ProjectAssignmentForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectEmployeeAssignment
        fields = [
            'company',
            'drive',
            'employee',
            'employee_name',
            'employee_code',
            'department',
            'designation',
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
        self.fields['company'].queryset = ProjectCompany.objects.order_by('name', '-updated_at')
        self.fields['drive'].queryset = ProjectDrive.objects.select_related('company').order_by('-drive_date', '-updated_at')
        self.fields['employee'].queryset = ExternalEmployee.objects.order_by('branch', 'full_name')
        if drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
        elif company:
            self.fields['company'].initial = company
            self.fields['drive'].queryset = ProjectDrive.objects.filter(company=company).order_by('-drive_date', '-updated_at')
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class ProjectInterviewForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectInterview
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
        self.fields['company'].queryset = ProjectCompany.objects.order_by('name', '-updated_at')
        self.fields['drive'].queryset = ProjectDrive.objects.select_related('company').order_by('-drive_date', '-updated_at')
        self.fields['assignment'].queryset = ProjectEmployeeAssignment.objects.select_related('employee', 'company', 'drive').order_by('-assigned_at')
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['company'].initial = assignment.company
            self.fields['drive'].initial = assignment.drive
        elif drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
            self.fields['assignment'].queryset = ProjectEmployeeAssignment.objects.filter(drive=drive).order_by('-assigned_at')
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


class ProjectAllocationForm(HRModelFormMixin, forms.ModelForm):
    class Meta:
        model = ProjectAllocation
        fields = ['assignment', 'company', 'billing_rate', 'allocation_status', 'allocation_date', 'release_date', 'remarks']
        widgets = {
            'allocation_date': forms.DateInput(attrs={'type': 'date'}),
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'remarks': forms.Textarea(attrs={'rows': 3}),
            'billing_rate': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 3-6 LPA'}),
        }

    def __init__(self, *args, **kwargs):
        assignment = kwargs.pop('assignment', None)
        super().__init__(*args, **kwargs)
        self.fields['assignment'].queryset = ProjectEmployeeAssignment.objects.select_related('employee', 'company', 'drive').order_by('-assigned_at')
        self.fields['company'].queryset = ProjectCompany.objects.order_by('name', '-updated_at')
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['company'].initial = assignment.company
        self.fields['billing_rate'].label = 'Package'
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()


