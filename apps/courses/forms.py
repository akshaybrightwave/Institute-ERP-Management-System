from django import forms
from .models import Course
from apps.categories.models import Category


class CourseForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Course Category",
        widget=forms.Select(attrs={'class': 'form-select dark-input'})
    )
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Course name'})
    )
    duration_value = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Duration'})
    )
    duration_unit = forms.ChoiceField(
        choices=[('Year', 'Year'), ('Month', 'Month'), ('Week', 'Week')],
        widget=forms.Select(attrs={'class': 'form-select dark-input'})
    )
    fees = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control dark-input', 'placeholder': 'Enter Course Fee'})
    )

    class Meta:
        model = Course
        fields = ['category', 'name', 'fees']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.duration:
            parts = self.instance.duration.split(' ', 1)
            if len(parts) == 2:
                self.initial['duration_value'] = parts[0]
                self.initial['duration_unit'] = parts[1]
            else:
                self.initial['duration_value'] = self.instance.duration
                self.initial['duration_unit'] = 'Year'

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get('name', '').strip()
        
        # Combine duration inputs
        dur_val = cleaned_data.get('duration_value', '').strip()
        dur_unit = cleaned_data.get('duration_unit', '')
        if dur_val and dur_unit:
            cleaned_data['duration'] = f"{dur_val} {dur_unit}"
        else:
            self.add_error('duration_value', 'Course duration is required.')

        # Check duplicates under the same center
        if name:
            center = None
            if self.user and self.user.role == 'center':
                center = self.user.center
            elif self.instance and self.instance.pk:
                center = self.instance.center
                
            qs = Course.objects.filter(name__iexact=name, center=center)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                self.add_error('name', 'Course with this name already exists.')

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if 'duration' in self.cleaned_data:
            instance.duration = self.cleaned_data['duration']
        if commit:
            instance.save()
        return instance
