import os
from django import forms
from django.db.models import Q
from .models import StudyMaterial
from apps.centers.models import Center
from apps.courses.models import Course


class StudyMaterialForm(forms.ModelForm):
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        required=True,
        empty_label="Select a Center",
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_center'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        required=True,
        empty_label="Select a Course",
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_course'})
    )

    class Meta:
        model = StudyMaterial
        fields = ['center', 'course', 'title', 'file_type', 'upload_file', 'external_url', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control text-white dark-input', 'placeholder': 'Enter Title'}),
            'file_type': forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_file_type'}),
            'upload_file': forms.ClearableFileInput(attrs={'class': 'form-control text-white dark-input', 'id': 'id_upload_file'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control text-white dark-input', 'placeholder': 'Enter External URL (e.g. YouTube Link)'}),
            'description': forms.Textarea(attrs={'class': 'form-control text-white dark-input', 'rows': 3, 'placeholder': 'Enter Description'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Handle center restriction
        if self.user and self.user.role == 'center':
            user_center = self.user.center
            self.fields['center'].queryset = Center.objects.filter(id=user_center.id)
            self.fields['center'].initial = user_center
            self.fields['center'].widget.attrs.update({'disabled': 'disabled'})
            self.fields['course'].queryset = Course.objects.filter(Q(center=user_center) | Q(center__isnull=True))
        else:
            self.fields['center'].queryset = Center.objects.all().order_by('name')
            self.fields['course'].queryset = Course.objects.all().order_by('name')

        # Dynamically set course choices if POSTing or editing
        center_id = None
        if self.is_bound:
            center_id = self.data.get('center')
        elif self.instance and self.instance.pk:
            center_id = self.instance.center.id

        if center_id:
            if self.user and self.user.role == 'center':
                center_id = self.user.center.id
            self.fields['course'].queryset = Course.objects.filter(Q(center_id=center_id) | Q(center__isnull=True)).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        center = cleaned_data.get('center')
        course = cleaned_data.get('course')
        title = cleaned_data.get('title')
        file_type = cleaned_data.get('file_type')
        upload_file = cleaned_data.get('upload_file')
        external_url = cleaned_data.get('external_url')

        if self.user and self.user.role == 'center':
            center = self.user.center
            cleaned_data['center'] = center

        if not center or not course:
            raise forms.ValidationError("Both Center and Course must be selected.")

        # Duplicate check: Center + Course + Title
        dup_qs = StudyMaterial.objects.filter(
            center=center,
            course=course,
            title__iexact=title
        )
        if self.instance and self.instance.pk:
            dup_qs = dup_qs.exclude(pk=self.instance.pk)
        if dup_qs.exists():
            raise forms.ValidationError("A study material with this title already exists for the selected Center and Course.")

        # Validate file or URL matching the file type
        if file_type == 'Video Link':
            if not external_url:
                self.add_error('external_url', "An external URL is required when File Type is Video Link.")
        else:
            if not upload_file and not self.instance.upload_file:
                self.add_error('upload_file', "A file must be selected for upload.")

        # Validate File Size & Format/Extension
        if upload_file:
            # Check maximum size (50 MB)
            max_size = 50 * 1024 * 1024  # 50MB in bytes
            if upload_file.size > max_size:
                self.add_error('upload_file', "Maximum file upload size is 50 MB.")

            # Validate extension matching the selected file_type
            filename = upload_file.name.lower()
            ext = os.path.splitext(filename)[1]

            allowed_exts = {
                'PDF File': ['.pdf'],
                'DOC File': ['.doc', '.docx'],
                'PPT File': ['.ppt', '.pptx'],
                'Excel File': ['.xls', '.xlsx', '.csv'],
                'ZIP File': ['.zip', '.rar', '.7z'],
                'Image': ['.jpg', '.jpeg', '.png', '.webp', '.gif'],
            }

            if file_type in allowed_exts:
                if ext not in allowed_exts[file_type]:
                    allowed_str = ", ".join(allowed_exts[file_type])
                    self.add_error('upload_file', f"Invalid file format. Allowed formats for {file_type}: {allowed_str}")

        return cleaned_data
