from django import forms
from .models import StudentProfile, StudentAdmission


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['full_name', 'phone', 'email', 'profile_picture', 'bio']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control'}),
        }


class StudentAdmissionForm(forms.ModelForm):
    admission_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'})
    )
    dob = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'})
    )

    class Meta:
        model = StudentAdmission
        exclude = ['status', 'approved_by', 'approved_at', 'cancelled_by', 'cancelled_at', 'cancel_reason']
        widgets = {
            'student_name': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Student Name', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'gender': forms.Select(choices=[('', 'Select Gender'), ('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'center': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'enrollment_no': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Enrollment No.', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'course': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'whatsapp_no': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Whatsapp Number', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'alt_mobile': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Mobile', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'email': forms.EmailInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter E-Mail ID', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Father Name', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'mother_name': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Mother Name', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'family_id': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter family ID', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'marital_status': forms.Select(choices=[('', 'Select Marital Status'), ('Married', 'Married'), ('Unmarried', 'Unmarried')], attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'category': forms.Select(choices=[('', 'Select Category'), ('General', 'General'), ('OBC', 'OBC'), ('SC', 'SC'), ('ST', 'ST')], attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'medium': forms.Select(choices=[('', 'Select Medium'), ('English', 'English'), ('Hindi', 'Hindi'), ('Other', 'Other')], attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'address': forms.Textarea(attrs={'class': 'form-control dark-input', 'placeholder': 'Address', 'rows': 3, 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'pincode': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Pincode', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'passed_exam': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Passed Exam', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'marks_grade': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Marks/Grade', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'board': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Board', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'passing_year': forms.DateInput(attrs={'type': 'date', 'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'aadhar_no': forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Aadhar No.', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        from apps.academics.models import TimeTable
        from apps.centers.models import Center
        self.fields['center'].empty_label = "Select a Center"
        self.fields['course'].empty_label = "Select a Course"
        
        if user and user.role == 'center':
            if user.center:
                self.fields['center'].queryset = Center.objects.filter(id=user.center.id)
                self.fields['center'].initial = user.center
                self.fields['center'].empty_label = None
                from apps.courses.models import Course
                self.fields['course'].queryset = Course.objects.filter(
                    assignments__center=user.center,
                    assignments__is_active=True
                ).distinct().order_by('name')
            else:
                self.fields['center'].queryset = Center.objects.none()
                from apps.courses.models import Course
                self.fields['course'].queryset = Course.objects.none()
        else:
            self.fields['center'].queryset = Center.objects.filter(
                center_user__is_active=True
            ).order_by('name')

        self.fields['timetable_course'].widget = forms.Select(
            choices=[('', 'Select a Course')] + [(t.timetable_name, t.timetable_name) for t in TimeTable.objects.all()],
            attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}
        )
        self.fields['state'].widget = forms.Select(
            choices=[
                ('', 'Select a State'),
                # States
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
                # Union Territories
                ('Andaman and Nicobar Islands', 'Andaman and Nicobar Islands'),
                ('Chandigarh', 'Chandigarh'),
                ('Dadra and Nagar Haveli and Daman and Diu', 'Dadra and Nagar Haveli and Daman and Diu'),
                ('Delhi', 'Delhi'),
                ('Jammu and Kashmir', 'Jammu and Kashmir'),
                ('Ladakh', 'Ladakh'),
                ('Lakshadweep', 'Lakshadweep'),
                ('Puducherry', 'Puducherry'),
            ],
            attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}
        )
        self.fields['district'].widget = forms.Select(
            choices=[('', 'Select a City'), ('Mumbai', 'Mumbai'), ('Thane', 'Thane'), ('Pune', 'Pune'), ('Surat', 'Surat')],
            attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}
        )

    def clean(self):
        cleaned_data = super().clean()
        user = getattr(self, 'user', None)
        if user and hasattr(user, 'role') and user.role == 'center' and getattr(user, 'center', None):
            cleaned_data['center'] = user.center
        return cleaned_data
