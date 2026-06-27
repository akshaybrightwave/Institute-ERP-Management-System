from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db import IntegrityError
from django.db.models import Q

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


TIME_SELECT_CHOICES = [('', '---------')]
for hour in range(24):
    for minute in range(0, 60, 5):
        value = f'{hour:02d}:{minute:02d}'
        label_hour = hour % 12 or 12
        meridiem = 'AM' if hour < 12 else 'PM'
        TIME_SELECT_CHOICES.append((value, f'{label_hour:02d}:{minute:02d} {meridiem}'))


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
            'experience': forms.TextInput(attrs={'placeholder': 'e.g. Fresher, 2 years, 1.5 years'}),
            'skills': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Python, Excel, Communication...'}),
            'current_salary': forms.TextInput(attrs={'placeholder': 'e.g. 3 LPA, 25000, Negotiable'}),
            'expected_salary': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 35000, Negotiable'}),
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
            'experience': forms.TextInput(attrs={'placeholder': 'e.g. Fresher, 2 years, 1.5 years'}),
            'skills': forms.Textarea(attrs={'rows': 3}),
            'current_salary': forms.TextInput(attrs={'placeholder': 'e.g. 3 LPA, 25000, Negotiable'}),
            'expected_salary': forms.TextInput(attrs={'placeholder': 'e.g. 5 LPA, 35000, Negotiable'}),
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
    user_entry = forms.CharField(
        label='Login User',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control external-user-combobox-input',
            'placeholder': 'Select or type login user',
        }),
    )
    personal_fields = ['full_name', 'mobile', 'email', 'dob', 'gender', 'address', 'emergency_contact']
    employment_fields = ['employee_id', 'user', 'user_entry', 'branch', 'department', 'designation', 'joining_date', 'employment_type', 'reporting_manager', 'status', 'scheduled_login_time', 'scheduled_logout_time']
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
            'scheduled_login_time',
            'scheduled_logout_time',
            'aadhaar',
            'pan',
            'resume',
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'joining_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_login_time': forms.Select(choices=TIME_SELECT_CHOICES),
            'scheduled_logout_time': forms.Select(choices=TIME_SELECT_CHOICES),
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
        self.fields['user'].required = False
        self.fields['user'].widget = forms.HiddenInput()
        self.fields['user'].label = 'Login User'
        selected_user = current_user if current_user and not allow_all_users else getattr(self.instance, 'user', None)
        if selected_user:
            self.fields['user_entry'].initial = self._user_label(selected_user)
        self.user_options = [
            {'id': str(user.pk), 'label': self._user_label(user)}
            for user in self.fields['user'].queryset
        ]
        self.order_fields([
            'full_name',
            'dob',
            'gender',
            'email',
            'mobile',
            'address',
            'emergency_contact',
            'employee_id',
            'user',
            'user_entry',
            'branch',
            'department',
            'designation',
            'joining_date',
            'employment_type',
            'reporting_manager',
            'status',
            'scheduled_login_time',
            'scheduled_logout_time',
            'aadhaar',
            'pan',
            'resume',
        ])
        self.fields['scheduled_login_time'].label = 'Login Time'
        self.fields['scheduled_logout_time'].label = 'Logout Time'
        self.apply_control_styles()

    def _user_label(self, user):
        display_name = user.get_full_name() or user.username
        if user.email:
            return f'{display_name} ({user.email})'
        return display_name

    def _resolve_user_from_entry(self, user_entry):
        user_entry = (user_entry or '').strip()
        if not user_entry:
            return None
        for option in getattr(self, 'user_options', []):
            if option['label'].casefold() == user_entry.casefold():
                return self.fields['user'].queryset.filter(pk=option['id']).first()
        return self.fields['user'].queryset.filter(
            Q(username__iexact=user_entry)
            | Q(email__iexact=user_entry)
            | Q(first_name__iexact=user_entry)
            | Q(last_name__iexact=user_entry)
        ).first()

    def clean(self):
        cleaned_data = super().clean()
        user_entry = (cleaned_data.get('user_entry') or '').strip()
        if user_entry:
            matched_user = self._resolve_user_from_entry(user_entry)
            if not matched_user:
                self.add_error('user_entry', 'No active login user matches this value.')
            else:
                cleaned_data['user'] = matched_user
        login_time = cleaned_data.get('scheduled_login_time')
        logout_time = cleaned_data.get('scheduled_logout_time')
        if login_time and logout_time and logout_time <= login_time:
            self.add_error('scheduled_logout_time', 'Logout time must be after login time.')
        return cleaned_data

    def save(self, commit=True):
        employee = super().save(commit=False)
        user_entry = (self.cleaned_data.get('user_entry') or '').strip()
        employee.user = self._resolve_user_from_entry(user_entry) if user_entry else None
        if commit:
            employee.save()
            self.save_m2m()
        return employee


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
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control hr-combobox-input',
            'list': 'placement-drive-company-options',
            'placeholder': 'Select or type company',
        }),
    )

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
        self.fields['company'].widget = forms.HiddenInput()
        if company:
            self.fields['company'].initial = company
            self.fields['company_entry'].initial = str(company)
        elif self.instance and self.instance.pk and self.instance.company:
            self.fields['company_entry'].initial = str(self.instance.company)
        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.order_fields([
            'company',
            'company_entry',
            'job_role',
            'drive_date',
            'package',
            'eligibility_criteria',
            'venue',
            'remarks',
            'status',
        ])
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return PlacementCompany.objects.filter(pk=option['id']).first()
        return PlacementCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def save(self, commit=True):
        drive = super().save(commit=False)
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()
        company = drive.company or self._resolve_company_from_entry(company_entry)
        if company_entry and not company:
            company = PlacementCompany.objects.create(name=company_entry)
        drive.company = company
        if commit:
            drive.save()
            self.save_m2m()
        return drive


class PlacementAssignmentForm(HRModelFormMixin, forms.ModelForm):
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control hr-combobox-input',
            'list': 'placement-company-options',
            'placeholder': 'Select or type company',
        }),
    )
    drive_entry = forms.CharField(
        label='Drive',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control hr-combobox-input',
            'list': 'placement-drive-options',
            'placeholder': 'Select or type drive',
        }),
    )

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
        self.fields['company'].widget = forms.HiddenInput()
        self.fields['drive'].widget = forms.HiddenInput()
        self.fields['student_name'].label = 'Employee Name'
        self.fields['course_name'].label = 'Designation'
        if drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
            self.fields['drive_entry'].initial = str(drive)
            if drive.company:
                self.fields['company_entry'].initial = str(drive.company)
        elif company:
            self.fields['company'].initial = company
            self.fields['drive'].queryset = PlacementDrive.objects.filter(company=company).order_by('-drive_date', '-updated_at')
            self.fields['company_entry'].initial = str(company)
        elif self.instance and self.instance.pk:
            if self.instance.company:
                self.fields['company_entry'].initial = str(self.instance.company)
            if self.instance.drive:
                self.fields['drive_entry'].initial = str(self.instance.drive)

        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.drive_options = [
            {
                'id': str(drive.pk),
                'label': str(drive),
                'company_id': str(drive.company_id or ''),
                'company_label': str(drive.company) if drive.company else '',
            }
            for drive in self.fields['drive'].queryset
        ]
        self.order_fields([
            'company',
            'drive',
            'company_entry',
            'drive_entry',
            'student_name',
            'course_name',
            'percentage_or_cgpa',
            'skills',
            'interview_status',
            'final_status',
        ])
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return PlacementCompany.objects.filter(pk=option['id']).first()
        return PlacementCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def _resolve_drive_from_entry(self, drive_entry):
        drive_entry = (drive_entry or '').strip()
        if not drive_entry:
            return None
        for option in self.drive_options:
            if option['label'].casefold() == drive_entry.casefold():
                return PlacementDrive.objects.filter(pk=option['id']).select_related('company').first()
        return None

    def save(self, commit=True):
        assignment = super().save(commit=False)
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()
        drive_entry = (self.cleaned_data.get('drive_entry') or '').strip()

        company = assignment.company or self._resolve_company_from_entry(company_entry)
        if company_entry and not company:
            company = PlacementCompany.objects.create(name=company_entry)

        drive = assignment.drive or self._resolve_drive_from_entry(drive_entry)
        if drive_entry and not drive:
            drive_queryset = PlacementDrive.objects.filter(job_role__iexact=drive_entry)
            drive_queryset = drive_queryset.filter(company=company) if company else drive_queryset.filter(company__isnull=True)
            drive = drive_queryset.order_by('-drive_date', '-updated_at').first()
            if not drive:
                drive = PlacementDrive.objects.create(company=company, job_role=drive_entry)

        if drive and not company:
            company = drive.company

        assignment.company = company
        assignment.drive = drive
        if commit:
            assignment.save()
            self.save_m2m()
        return assignment



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
    assignment_entry = forms.CharField(
        label='Assignment',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control hr-combobox-input',
            'list': 'placement-offer-assignment-options',
            'placeholder': 'Select or type assignment',
        }),
    )
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control hr-combobox-input',
            'list': 'placement-offer-company-options',
            'placeholder': 'Select or type company',
        }),
    )

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
        self.fields['assignment'].widget = forms.HiddenInput()
        self.fields['company'].widget = forms.HiddenInput()
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['assignment_entry'].initial = self._assignment_label(assignment)
            self.fields['company'].initial = assignment.company
            if assignment.company:
                self.fields['company_entry'].initial = str(assignment.company)
        elif self.instance and self.instance.pk:
            if self.instance.assignment:
                self.fields['assignment_entry'].initial = self._assignment_label(self.instance.assignment)
            if self.instance.company:
                self.fields['company_entry'].initial = str(self.instance.company)
        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.assignment_options = [
            {
                'id': str(assignment.pk),
                'label': self._assignment_label(assignment),
                'company_id': str(assignment.company_id or ''),
                'company_label': str(assignment.company) if assignment.company else '',
            }
            for assignment in self.fields['assignment'].queryset
        ]
        self.order_fields([
            'assignment',
            'company',
            'assignment_entry',
            'company_entry',
            'offered_package',
            'offer_status',
            'joining_status',
            'joining_date',
            'remarks',
        ])
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _assignment_label(self, assignment):
        label = assignment.display_name
        if assignment.company:
            return f'{label} - {assignment.company}'
        return label

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return PlacementCompany.objects.filter(pk=option['id']).first()
        return PlacementCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def _resolve_assignment_from_entry(self, assignment_entry):
        assignment_entry = (assignment_entry or '').strip()
        if not assignment_entry:
            return None
        for option in self.assignment_options:
            if option['label'].casefold() == assignment_entry.casefold():
                return PlacementStudentAssignment.objects.filter(pk=option['id']).select_related('company').first()
        for assignment in self.fields['assignment'].queryset:
            if assignment.display_name.casefold() == assignment_entry.casefold():
                return assignment
        return None

    def save(self, commit=True):
        offer = super().save(commit=False)
        assignment_entry = (self.cleaned_data.get('assignment_entry') or '').strip()
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()
        company = self._resolve_company_from_entry(company_entry) if company_entry else None
        assignment = offer.assignment or self._resolve_assignment_from_entry(assignment_entry)
        if not company and offer.company:
            company = offer.company
        if not company and assignment:
            company = assignment.company
        if company_entry and not company:
            company = PlacementCompany.objects.create(name=company_entry)
        if assignment_entry and not assignment:
            assignment = PlacementStudentAssignment.objects.create(
                student_name=assignment_entry,
                company=company,
            )
        offer.assignment = assignment
        offer.company = company
        if commit:
            offer.save()
            self.save_m2m()
        return offer


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
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type company',
        }),
    )

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
        self.fields['company'].widget = forms.HiddenInput()
        if company:
            self.fields['company'].initial = company
            self.fields['company_entry'].initial = str(company)
        elif self.instance and self.instance.pk and self.instance.company:
            self.fields['company_entry'].initial = str(self.instance.company)
        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.order_fields([
            'company',
            'company_entry',
            'project_name',
            'role_required',
            'drive_date',
            'project_value',
            'eligibility_criteria',
            'venue',
            'remarks',
            'status',
        ])
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return ProjectCompany.objects.filter(pk=option['id']).first()
        return ProjectCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def save(self, commit=True):
        drive = super().save(commit=False)
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()
        company = drive.company or self._resolve_company_from_entry(company_entry)
        if company_entry and not company:
            company = ProjectCompany.objects.create(name=company_entry)
        drive.company = company
        if commit:
            drive.save()
            self.save_m2m()
        return drive


class ProjectAssignmentForm(HRModelFormMixin, forms.ModelForm):
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type company',
        }),
    )
    drive_entry = forms.CharField(
        label='Drive',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type drive',
        }),
    )
    employee_entry = forms.CharField(
        label='Employee',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type employee',
        }),
    )

    class Meta:
        model = ProjectEmployeeAssignment
        fields = [
            'company',
            'drive',
            'employee',
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
        self.fields['company'].widget = forms.HiddenInput()
        self.fields['drive'].widget = forms.HiddenInput()
        self.fields['employee'].widget = forms.HiddenInput()
        if drive:
            self.fields['drive'].initial = drive
            self.fields['company'].initial = drive.company
            self.fields['drive_entry'].initial = str(drive)
            if drive.company:
                self.fields['company_entry'].initial = str(drive.company)
        elif company:
            self.fields['company'].initial = company
            self.fields['drive'].queryset = ProjectDrive.objects.filter(company=company).order_by('-drive_date', '-updated_at')
            self.fields['company_entry'].initial = str(company)
        elif self.instance and self.instance.pk:
            if self.instance.company:
                self.fields['company_entry'].initial = str(self.instance.company)
            if self.instance.drive:
                self.fields['drive_entry'].initial = str(self.instance.drive)
            if self.instance.employee:
                self.fields['employee_entry'].initial = self._employee_label(self.instance.employee)
            elif self.instance.employee_name:
                self.fields['employee_entry'].initial = self.instance.employee_name

        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.drive_options = [
            {
                'id': str(drive.pk),
                'label': str(drive),
                'company_id': str(drive.company_id or ''),
                'company_label': str(drive.company) if drive.company else '',
            }
            for drive in self.fields['drive'].queryset
        ]
        self.employee_options = [
            {
                'id': str(employee.pk),
                'label': self._employee_label(employee),
                'code': employee.employee_id or '',
                'department': employee.department or '',
                'designation': employee.designation or '',
            }
            for employee in self.fields['employee'].queryset
        ]
        self.order_fields([
            'company',
            'drive',
            'employee',
            'company_entry',
            'drive_entry',
            'employee_entry',
            'employee_code',
            'department',
            'designation',
            'skills',
            'interview_status',
            'final_status',
        ])
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _employee_label(self, employee):
        label = employee.full_name or employee.employee_id or f'Employee #{employee.pk}'
        if employee.employee_id and employee.employee_id != label:
            return f'{label} ({employee.employee_id})'
        return label

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return ProjectCompany.objects.filter(pk=option['id']).first()
        return ProjectCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def _resolve_drive_from_entry(self, drive_entry):
        drive_entry = (drive_entry or '').strip()
        if not drive_entry:
            return None
        for option in self.drive_options:
            if option['label'].casefold() == drive_entry.casefold():
                return ProjectDrive.objects.filter(pk=option['id']).select_related('company').first()
        return None

    def _resolve_employee_from_entry(self, employee_entry):
        employee_entry = (employee_entry or '').strip()
        if not employee_entry:
            return None
        for option in self.employee_options:
            if option['label'].casefold() == employee_entry.casefold():
                return ExternalEmployee.objects.filter(pk=option['id']).first()
        return ExternalEmployee.objects.filter(
            Q(full_name__iexact=employee_entry)
            | Q(employee_id__iexact=employee_entry)
            | Q(email__iexact=employee_entry)
            | Q(mobile__iexact=employee_entry)
        ).first()

    def save(self, commit=True):
        assignment = super().save(commit=False)
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()
        drive_entry = (self.cleaned_data.get('drive_entry') or '').strip()
        employee_entry = (self.cleaned_data.get('employee_entry') or '').strip()

        company = assignment.company or self._resolve_company_from_entry(company_entry)
        if company_entry and not company:
            company = ProjectCompany.objects.create(name=company_entry)

        drive = assignment.drive or self._resolve_drive_from_entry(drive_entry)
        if drive_entry and not drive:
            drive_queryset = ProjectDrive.objects.filter(project_name__iexact=drive_entry)
            drive_queryset = drive_queryset.filter(company=company) if company else drive_queryset.filter(company__isnull=True)
            drive = drive_queryset.order_by('-drive_date', '-updated_at').first()
            if not drive:
                drive = ProjectDrive.objects.create(company=company, project_name=drive_entry)

        if drive and not company:
            company = drive.company

        employee = assignment.employee or self._resolve_employee_from_entry(employee_entry)
        assignment.company = company
        assignment.drive = drive
        assignment.employee = employee
        if employee:
            assignment.employee_name = employee.full_name
            assignment.employee_code = assignment.employee_code or employee.employee_id
            assignment.department = assignment.department or employee.department
            assignment.designation = assignment.designation or employee.designation
        else:
            assignment.employee_name = employee_entry

        if commit:
            assignment.save()
            self.save_m2m()
        return assignment


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
    assignment_entry = forms.CharField(
        label='Assignment',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type assignment',
        }),
    )
    company_entry = forms.CharField(
        label='Company',
        required=False,
        widget=forms.TextInput(attrs={
            'autocomplete': 'off',
            'class': 'form-control project-combobox-input',
            'placeholder': 'Select or type company',
        }),
    )

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
        self.fields['assignment'].widget = forms.HiddenInput()
        self.fields['company'].widget = forms.HiddenInput()
        if assignment:
            self.fields['assignment'].initial = assignment
            self.fields['assignment_entry'].initial = self._assignment_label(assignment)
            self.fields['company'].initial = assignment.company
            if assignment.company:
                self.fields['company_entry'].initial = str(assignment.company)
        elif self.instance and self.instance.pk:
            if self.instance.assignment:
                self.fields['assignment_entry'].initial = self._assignment_label(self.instance.assignment)
            if self.instance.company:
                self.fields['company_entry'].initial = str(self.instance.company)
        self.assignment_options = [
            {
                'id': str(assignment.pk),
                'label': self._assignment_label(assignment),
                'company_id': str(assignment.company_id or ''),
                'company_label': str(assignment.company) if assignment.company else '',
            }
            for assignment in self.fields['assignment'].queryset
        ]
        self.company_options = [
            {'id': str(company.pk), 'label': str(company)}
            for company in self.fields['company'].queryset
        ]
        self.order_fields([
            'assignment',
            'company',
            'assignment_entry',
            'company_entry',
            'billing_rate',
            'allocation_status',
            'allocation_date',
            'release_date',
            'remarks',
        ])
        self.fields['billing_rate'].label = 'Package'
        for field in self.fields.values():
            field.required = False
        self.apply_control_styles()

    def _assignment_label(self, assignment):
        label = assignment.display_name
        if assignment.company:
            return f'{label} - {assignment.company}'
        return label

    def _resolve_assignment_from_entry(self, assignment_entry):
        assignment_entry = (assignment_entry or '').strip()
        if not assignment_entry:
            return None
        for option in self.assignment_options:
            if option['label'].casefold() == assignment_entry.casefold():
                return ProjectEmployeeAssignment.objects.filter(pk=option['id']).select_related('company').first()
        for assignment in self.fields['assignment'].queryset:
            if assignment.display_name.casefold() == assignment_entry.casefold():
                return assignment
        return None

    def _resolve_company_from_entry(self, company_entry):
        company_entry = (company_entry or '').strip()
        if not company_entry:
            return None
        for option in self.company_options:
            if option['label'].casefold() == company_entry.casefold():
                return ProjectCompany.objects.filter(pk=option['id']).first()
        return ProjectCompany.objects.filter(name__iexact=company_entry).order_by('name', '-updated_at').first()

    def save(self, commit=True):
        allocation = super().save(commit=False)
        assignment_entry = (self.cleaned_data.get('assignment_entry') or '').strip()
        company_entry = (self.cleaned_data.get('company_entry') or '').strip()

        company = self._resolve_company_from_entry(company_entry) if company_entry else allocation.company
        assignment = allocation.assignment or self._resolve_assignment_from_entry(assignment_entry)
        if company_entry and not company:
            company = ProjectCompany.objects.create(name=company_entry)
        if not company and assignment:
            company = assignment.company
        if assignment_entry and not assignment:
            assignment = ProjectEmployeeAssignment.objects.create(employee_name=assignment_entry, company=company)

        allocation.assignment = assignment
        allocation.company = company
        if commit:
            allocation.save()
            self.save_m2m()
        return allocation


