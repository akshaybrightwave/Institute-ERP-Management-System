from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Inquiry, Lead, CallLog, FollowUp, CounselingSession, VisitSheet, AdmissionSheet

ADMIN_ROLES = ('admin', 'superadmin')
MANAGED_USER_ROLES = ('admin', 'hr', 'telecaller', 'counselor')


class ManagementUserCreateForm(forms.Form):
    role = forms.ChoiceField(choices=())
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=20)
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['role'].choices = tuple(
            choice for choice in User.ROLE_CHOICES if choice[0] in MANAGED_USER_ROLES
        )

    def clean_role(self):
        role = self.cleaned_data.get('role')
        if role not in MANAGED_USER_ROLES:
            raise forms.ValidationError('Please select a valid role.')
        return role

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        User = get_user_model()
        if User.all_objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('An account with this username already exists.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        User = get_user_model()
        if User.all_objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        digits = ''.join(char for char in phone if char.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError('Phone number must be between 10 and 15 digits.')
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', 'Passwords do not match.')
        if password:
            try:
                validate_password(password)
            except forms.ValidationError as exc:
                self.add_error('password', exc)
        return cleaned_data

    def save(self):
        User = get_user_model()
        user = User.all_objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'].strip(),
            last_name=self.cleaned_data['last_name'].strip(),
            role=self.cleaned_data['role'],
            is_active=True,
            is_deleted=False,
        )
        return user

class InquiryForm(forms.ModelForm):
    class Meta:
        model = Inquiry
        fields = ['full_name', 'mobile_number', 'email', 'city', 'course_interest', 'source', 'remarks', 'status']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Full Name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Mobile Number'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter Email (Optional)'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter City'}),
            'course_interest': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Course of Interest'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Remarks'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_mobile_number(self):
        mobile = self.cleaned_data.get('mobile_number', '').strip()
        if not mobile:
            raise forms.ValidationError("Mobile number is required.")
        # Ensure it has only digits and optional '+' prefix, and length is 10 to 15
        digits = ''.join(c for c in mobile if c.isdigit())
        if len(digits) < 10 or len(digits) > 15:
            raise forms.ValidationError("Mobile number must be between 10 and 15 digits.")
        
        # Prevent duplicate inquiries by mobile number
        qs = Inquiry.objects.filter(mobile_number=mobile)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An inquiry with this mobile number already exists.")
            
        return mobile


class LeadConversionForm(forms.Form):
    """Form used during Inquiry → Lead conversion.
    Requires telecaller to select an active counselor before the lead is created.
    """
    assigned_counselor = forms.ModelChoiceField(
        queryset=None,          # populated in __init__ to get fresh queryset each time
        required=True,
        empty_label="— Select Assigned Counselor —",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'id_assigned_counselor',
        }),
        label="Assigned Counselor",
        error_messages={'required': 'Please select a counselor before converting this inquiry.'},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields['assigned_counselor'].queryset = (
            User.objects.filter(role='counselor', is_active=True)
                        .order_by('username')
        )


class LeadForm(forms.ModelForm):
    class Meta:
        model = Lead
        fields = ['status', 'priority', 'next_followup_date', 'notes']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'next_followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter follow-up details or notes'}),
        }


class CallLogForm(forms.ModelForm):
    class Meta:
        model = CallLog
        fields = ['call_duration', 'call_status', 'remarks']
        widgets = {
            'call_duration': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Duration in seconds'}),
            'call_status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Call summary...'}),
        }


class FollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['followup_date', 'next_followup_date', 'response', 'status']
        widgets = {
            'followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'response': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Response details...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class CounselingSessionForm(forms.ModelForm):
    class Meta:
        model = CounselingSession
        fields = ['lead', 'session_date', 'discussion_notes', 'career_guidance_notes', 'next_action']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'session_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'discussion_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Enter detailed discussion notes...'}),
            'career_guidance_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter career guidance notes (optional)...'}),
            'next_action': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Next call scheduled, Waiting for response...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.role in ADMIN_ROLES:
                self.fields['lead'].queryset = Lead.objects.all()
            else:
                self.fields['lead'].queryset = Lead.objects.filter(assigned_counselor=user)


class CounselorFollowUpForm(forms.ModelForm):
    class Meta:
        model = FollowUp
        fields = ['lead', 'followup_date', 'next_followup_date', 'response', 'outcome', 'status']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'next_followup_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'response': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Follow-up notes...'}),
            'outcome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Outcome...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.role in ADMIN_ROLES:
                self.fields['lead'].queryset = Lead.objects.all()
            else:
                self.fields['lead'].queryset = Lead.objects.filter(assigned_counselor=user)


class CounselorLeadStatusForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['counselor_status'].choices = [
            ('', '-- Select the option --'),
            ('INTERESTED', 'Interested'),
            ('NOT_INTERESTED', 'Not Interested'),
            ('ADMISSION', 'Admission'),
            ('FOLLOW_UP_REQUIRED', 'Pending Follow Up'),
        ]
    class Meta:
        model = Lead
        fields = ['counselor_status', 'notes']
        widgets = {
            'counselor_status': forms.Select(attrs={'class': 'form-select'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Add a remark or note about this status update...',
            }),
        }
        labels = {
            'notes': 'Remark',
        }


class VisitSheetForm(forms.ModelForm):
    class Meta:
        model = VisitSheet
        fields = ['lead', 'visit_date', 'visit_time', 'status', 'remarks']
        widgets = {
            'lead': forms.Select(attrs={'class': 'form-select'}),
            'visit_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'visit_time': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter remarks...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            if user.role in ADMIN_ROLES:
                self.fields['lead'].queryset = Lead.objects.all()
            else:
                self.fields['lead'].queryset = Lead.objects.filter(assigned_counselor=user)


class AdmissionSheetForm(forms.ModelForm):
    class Meta:
        model = AdmissionSheet
        fields = [
            'admission_date', 'admission_status',
            'student_name', 'mobile_number', 'email_id', 'parent_name', 'parent_mobile',
            'college_name', 'university_name', 'department', 'academic_year',
            'course_name', 'batch_name', 'admission_source',
            'seat_status', 'remarks', 'document_status', 'fee_status'
        ]
        widgets = {
            'admission_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'admission_status': forms.Select(attrs={'class': 'form-select'}),
            'student_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Student Name'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mobile Number'}),
            'email_id': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email (Optional)'}),
            'parent_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent Name'}),
            'parent_mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Parent Mobile'}),
            'college_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'College Name'}),
            'university_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'University Name'}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'}),
            'academic_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2026-2027'}),
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Course Name'}),
            'batch_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Batch Name'}),
            'admission_source': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Source'}),
            'seat_status': forms.Select(attrs={'class': 'form-select'}),
            'document_status': forms.Select(attrs={'class': 'form-select'}),
            'fee_status': forms.Select(attrs={'class': 'form-select'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Remarks...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.role not in ADMIN_ROLES:
            if 'document_status' in self.fields:
                del self.fields['document_status']
            if 'fee_status' in self.fields:
                del self.fields['fee_status']

