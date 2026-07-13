from django import forms
from .models import Center
from apps.accounts.models import User
import re

class CenterForm(forms.ModelForm):

    has_reception = forms.ChoiceField(label="Reception", choices=[(True, 'Yes'), (False, 'No')], widget=forms.Select(attrs={'class': 'form-select'}))
    has_staff_room = forms.ChoiceField(label="Staff Room", choices=[(True, 'Yes'), (False, 'No')], widget=forms.Select(attrs={'class': 'form-select'}))
    has_water_supply = forms.ChoiceField(label="Water Supply", choices=[(True, 'Yes'), (False, 'No')], widget=forms.Select(attrs={'class': 'form-select'}))
    has_toilet = forms.ChoiceField(label="Toilet", choices=[(True, 'Yes'), (False, 'No')], widget=forms.Select(attrs={'class': 'form-select'}))
    
    valid_upto = forms.DateField(label="Valid Upto", widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'Select A Date'}), required=True)
    owner_dob = forms.DateField(label="Date of birth", widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'Select date of birth'}), required=True)

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter Password (defaults to center123)'}),
        required=False
    )
    
    class Meta:
        model = Center
        fields = [
            'owner_name', 'name', 'head_qualification', 'prefix_roll_no', 
            'owner_dob', 'pan_number', 'aadhar_number',
            'address', 'owner_image', 'pincode', 'state', 'district',
            'staff_count', 'classrooms_count', 'computers_count', 'space_sqft',
            'whatsapp_number', 'phone', 'email',
            'has_reception', 'has_staff_room', 'has_water_supply', 'has_toilet',
            'valid_upto',
            'aadhar_doc', 'signature_doc', 'logo_doc', 'address_proof', 'agreement_doc'
        ]
        labels = {
            'owner_name': 'Institute Owner Name',
            'name': 'Institute Name',
            'head_qualification': 'Qualification of institute head',
            'prefix_roll_no': 'Prefix Roll No.',
            'pan_number': 'Pan Number',
            'aadhar_number': 'Aadhar Number',
            'address': 'Institite Full Address',
            'owner_image': 'Upload Image of franchise Owner',
            'pincode': 'Pincode',
            'state': 'Select State',
            'district': 'Select District',
            'staff_count': 'Number of Staff',
            'classrooms_count': 'Number of class rooms',
            'computers_count': 'Total Computers',
            'space_sqft': 'Space of Computer Center',
            'whatsapp_number': 'Whatsapp Number',
            'phone': 'Contact Number',
            'email': 'E-Mail ID',
            'aadhar_doc': 'Aadhar Card',
            'signature_doc': 'Signature',
            'logo_doc': 'Centre Logo',
            'address_proof': 'Address Proof',
            'agreement_doc': 'Agreement'
        }
        widgets = {
            'owner_name': forms.TextInput(attrs={'placeholder': 'Enter Institute Owner Name'}),
            'name': forms.TextInput(attrs={'placeholder': 'Enter Institute Name'}),
            'head_qualification': forms.TextInput(attrs={'placeholder': 'Enter Qualification of institute head'}),
            'prefix_roll_no': forms.TextInput(attrs={'placeholder': 'Enter Prefix Roll No.'}),
            'pan_number': forms.TextInput(attrs={'placeholder': 'Enter Pan Number'}),
            'aadhar_number': forms.TextInput(attrs={'placeholder': 'Enter Aadhar Number'}),
            'address': forms.Textarea(attrs={'placeholder': 'Institite Full Address', 'rows': 2}),
            'pincode': forms.TextInput(attrs={'placeholder': 'Enter Pincode'}),
            'state': forms.Select(attrs={'class': 'form-select'}),
            'district': forms.Select(attrs={'class': 'form-select'}),
            'staff_count': forms.NumberInput(attrs={'placeholder': 'Enter Number of computer operators'}),
            'classrooms_count': forms.NumberInput(attrs={'placeholder': 'Enter Number of class rooms'}),
            'computers_count': forms.NumberInput(attrs={'placeholder': 'Enter Total Computers'}),
            'space_sqft': forms.NumberInput(attrs={'placeholder': 'Enter Space of Computer Center'}),
            'whatsapp_number': forms.TextInput(attrs={'placeholder': 'Enter Whatsapp Number'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Enter Contact Number'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Enter E-Mail ID'}),
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            if isinstance(self.fields[field].widget, forms.CheckboxInput):
                self.fields[field].widget.attrs.update({'class': 'form-check-input'})
            elif isinstance(self.fields[field].widget, forms.Select):
                self.fields[field].widget.attrs.update({'class': 'form-select'})
            elif isinstance(self.fields[field].widget, forms.FileInput):
                self.fields[field].widget.attrs.update({'class': 'form-control'})
            else:
                if 'class' not in self.fields[field].widget.attrs:
                    self.fields[field].widget.attrs.update({'class': 'form-control'})
                else:
                    self.fields[field].widget.attrs['class'] += ' form-control'
                
        # Make fields required as per prompt
        is_update = self.instance and self.instance.pk
        for f in ['owner_name', 'name', 'head_qualification', 'prefix_roll_no', 'owner_dob',
                  'pan_number', 'aadhar_number', 'address', 'pincode', 'state', 'district',
                  'staff_count', 'classrooms_count', 'computers_count', 'space_sqft',
                  'whatsapp_number', 'phone', 'email', 'valid_upto']:
            if f in self.fields:
                self.fields[f].required = True

        for f in ['owner_image', 'aadhar_doc', 'signature_doc', 'logo_doc']:
            if f in self.fields:
                self.fields[f].required = not is_update
                
        # Optional files
        self.fields['address_proof'].required = False
        self.fields['agreement_doc'].required = False

        if is_update:
            self.fields['password'].required = False

        # Custom placeholders for empty dropdowns
        state_choices = [
            ('', 'Select a State'),
            ('Andhra Pradesh', 'Andhra Pradesh'),
            ('Arunachal Pradesh', 'Arunachal Pradesh'),
            ('Assam', 'Assam'),
            ('Bihar', 'Bihar'),
            ('Chhattisgarh', 'Chhattisgarh'),
            ('Goa', 'Goa'),
            ('Gujarat', 'Gujarat'),
            ('Haryana', 'Haryana'),
            ('Himachal Pradesh', 'Himachal Pradesh'),
            ('Jharkhand', 'Jharkhand'),
            ('Karnataka', 'Karnataka'),
            ('Kerala', 'Kerala'),
            ('Madhya Pradesh', 'Madhya Pradesh'),
            ('Maharashtra', 'Maharashtra'),
            ('Manipur', 'Manipur'),
            ('Meghalaya', 'Meghalaya'),
            ('Mizoram', 'Mizoram'),
            ('Nagaland', 'Nagaland'),
            ('Odisha', 'Odisha'),
            ('Punjab', 'Punjab'),
            ('Rajasthan', 'Rajasthan'),
            ('Sikkim', 'Sikkim'),
            ('Tamil Nadu', 'Tamil Nadu'),
            ('Telangana', 'Telangana'),
            ('Tripura', 'Tripura'),
            ('Uttar Pradesh', 'Uttar Pradesh'),
            ('Uttarakhand', 'Uttarakhand'),
            ('West Bengal', 'West Bengal'),
            ('Andaman and Nicobar Islands', 'Andaman and Nicobar Islands'),
            ('Chandigarh', 'Chandigarh'),
            ('Dadra and Nagar Haveli and Daman and Diu', 'Dadra and Nagar Haveli and Daman and Diu'),
            ('Delhi', 'Delhi'),
            ('Jammu and Kashmir', 'Jammu and Kashmir'),
            ('Ladakh', 'Ladakh'),
            ('Lakshadweep', 'Lakshadweep'),
            ('Puducherry', 'Puducherry'),
        ]
        
        if 'state' in self.fields:
            self.fields['state'].widget.choices = state_choices
            
        if 'district' in self.fields:
            self.fields['district'].widget.choices = [('', 'Select a City')]

    def clean_email(self):
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance and self.instance.pk and hasattr(self.instance, 'center_user') and self.instance.center_user:
            qs = qs.exclude(pk=self.instance.center_user.pk)
        if qs.exists():
            raise forms.ValidationError("Email is already in use by another account.")
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if not re.match(r'^\d{10}$', phone):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return phone
        
    def clean_whatsapp_number(self):
        whatsapp_number = self.cleaned_data.get('whatsapp_number')
        if not re.match(r'^\d{10}$', whatsapp_number):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return whatsapp_number

    def clean_pan_number(self):
        pan = self.cleaned_data.get('pan_number')
        if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$', str(pan).upper()):
            raise forms.ValidationError("Enter a valid PAN number.")
        return str(pan).upper()
        
    def clean_aadhar_number(self):
        aadhar = self.cleaned_data.get('aadhar_number')
        if not re.match(r'^\d{12}$', aadhar):
            raise forms.ValidationError("Enter a valid 12-digit Aadhar number.")
        return aadhar

from .models import CenterCertificate

class CenterCertificateForm(forms.ModelForm):
    class Meta:
        model = CenterCertificate
        fields = ['center', 'issue_date', 'valid_upto', 'certificate_status']
        widgets = {
            'center': forms.Select(attrs={'class': 'form-select'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'valid_upto': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'certificate_status': forms.Select(choices=[('Active', 'Active'), ('Expired', 'Expired'), ('Revoked', 'Revoked')], attrs={'class': 'form-select'})
        }


class CenterCertificateUpdateForm(forms.ModelForm):
    class Meta:
        model = CenterCertificate
        fields = ['issue_date', 'valid_upto', 'certificate_status']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'valid_upto': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'certificate_status': forms.Select(choices=[('Active', 'Active'), ('Expired', 'Expired'), ('Revoked', 'Revoked')], attrs={'class': 'form-select'})
        }
