from django import forms
from .models import Inquiry, Lead, CallLog, FollowUp

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
