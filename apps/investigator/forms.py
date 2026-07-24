from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import inlineformset_factory
from django.utils import timezone

from apps.accounts.models import User

from .models import CaseWorkItem, CaseWorkReport, FraudType, PoliceStation, RecoveryReport


class ActiveNameForm(forms.ModelForm):
    name = forms.CharField(
        strip=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if not name:
            raise forms.ValidationError('Name is required.')

        qs = self.Meta.model.objects.filter(name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('This name already exists.')
        return name


class FraudTypeForm(ActiveNameForm):
    class Meta:
        model = FraudType
        fields = ['name', 'is_active']


class PoliceStationForm(ActiveNameForm):
    class Meta:
        model = PoliceStation
        fields = ['name', 'is_active']


class InvestigatorUserCreateForm(UserCreationForm):
    first_name = forms.CharField(
        label='Name',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'autofocus': True, 'placeholder': 'Investigator name'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login username'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm password'})
        self.fields['password1'].help_text = ''
        self.fields['password2'].help_text = ''

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'investigator'
        user.is_active = True
        if commit:
            user.save()
        return user


class InvestigatorUserEditForm(forms.ModelForm):
    password1 = forms.CharField(
        label='New Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Leave blank to keep same password'}),
    )
    password2 = forms.CharField(
        label='Confirm New Password',
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'username', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Investigator name'}),
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Login username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 or password2:
            if password1 != password2:
                self.add_error('password2', 'Passwords do not match.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'investigator'
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class RecoveryReportForm(forms.ModelForm):
    ALLOWED_ATTACHMENT_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.gif', '.webp', '.xls', '.xlsx', '.doc', '.docx'}

    report_month = forms.ChoiceField(
        choices=[(month, month) for month in range(1, 13)],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    report_year = forms.IntegerField(
        min_value=2000,
        max_value=2100,
        initial=timezone.localdate().year,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = RecoveryReport
        fields = [
            'report_month',
            'report_year',
            'entry_date',
            'police_station',
            'fraud_type',
            'mobile_recovery_count',
            'financial_recovery_amount',
            'attachment',
        ]
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'police_station': forms.Select(attrs={'class': 'form-select'}),
            'fraud_type': forms.Select(attrs={'class': 'form-select'}),
            'mobile_recovery_count': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'financial_recovery_amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'step': '0.01'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['police_station'].queryset = PoliceStation.objects.filter(is_active=True).order_by('name')
        self.fields['police_station'].empty_label = 'Select police station'
        self.fields['fraud_type'].queryset = FraudType.objects.filter(is_active=True).order_by('name')
        self.fields['fraud_type'].empty_label = 'Select fraud type'

        if self.instance.pk:
            if self.instance.police_station_id:
                self.fields['police_station'].queryset = PoliceStation.objects.filter(
                    pk=self.instance.police_station_id
                ) | self.fields['police_station'].queryset
            if self.instance.fraud_type_id:
                self.fields['fraud_type'].queryset = FraudType.objects.filter(
                    pk=self.instance.fraud_type_id
                ) | self.fields['fraud_type'].queryset

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if not attachment:
            return attachment

        name = attachment.name.lower()
        if not any(name.endswith(ext) for ext in self.ALLOWED_ATTACHMENT_EXTENSIONS):
            raise forms.ValidationError('Upload PDF, image, Excel, or Word document only.')
        return attachment


class CaseWorkReportForm(forms.ModelForm):
    ALLOWED_ATTACHMENT_EXTENSIONS = RecoveryReportForm.ALLOWED_ATTACHMENT_EXTENSIONS

    class Meta:
        model = CaseWorkReport
        fields = [
            'case_no',
            'police_station',
            'investigating_officer',
            'case_status',
            'entry_date',
            'attachment',
        ]
        widgets = {
            'case_no': forms.TextInput(attrs={'class': 'form-control'}),
            'police_station': forms.Select(attrs={'class': 'form-select'}),
            'investigating_officer': forms.TextInput(attrs={'class': 'form-control'}),
            'case_status': forms.Select(attrs={'class': 'form-select'}),
            'entry_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'attachment': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['police_station'].queryset = PoliceStation.objects.filter(is_active=True).order_by('name')
        self.fields['police_station'].empty_label = 'Select police station'
        if self.instance.pk and self.instance.police_station_id:
            self.fields['police_station'].queryset = PoliceStation.objects.filter(
                pk=self.instance.police_station_id
            ) | self.fields['police_station'].queryset

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if not attachment:
            return attachment

        name = attachment.name.lower()
        if not any(name.endswith(ext) for ext in self.ALLOWED_ATTACHMENT_EXTENSIONS):
            raise forms.ValidationError('Upload PDF, image, Excel, or Word document only.')
        return attachment


class CaseWorkItemForm(forms.ModelForm):
    class Meta:
        model = CaseWorkItem
        fields = ['work_title', 'work_description']
        widgets = {
            'work_title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Work title'}),
            'work_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Work description'}),
        }


CaseWorkItemFormSet = inlineformset_factory(
    CaseWorkReport,
    CaseWorkItem,
    form=CaseWorkItemForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
