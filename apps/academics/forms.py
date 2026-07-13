from django import forms
from .models import TimeTable, AcademicSession, Occupation


class TimeTableForm(forms.ModelForm):
    class Meta:
        model = TimeTable
        fields = ['timetable_name']
        error_messages = {
            'timetable_name': {
                'required': 'Enter Time Table Name',
                'invalid': 'Enter Time Table Name'
            }
        }

    def clean_timetable_name(self):
        name = self.cleaned_data.get('timetable_name')
        if name:
            name = name.strip()
        return name


class AcademicSessionForm(forms.ModelForm):
    class Meta:
        model = AcademicSession
        fields = ['session_name']
        error_messages = {
            'session_name': {
                'required': 'Enter Session Name',
                'invalid': 'Enter Session Name'
            }
        }

    def clean_session_name(self):
        name = self.cleaned_data.get('session_name')
        if name:
            name = name.strip()
        return name


class OccupationForm(forms.ModelForm):
    class Meta:
        model = Occupation
        fields = ['occupation_name']
        error_messages = {
            'occupation_name': {
                'required': 'Enter Occupation Name',
                'invalid': 'Enter Occupation Name'
            }
        }

    def clean_occupation_name(self):
        name = self.cleaned_data.get('occupation_name')
        if name:
            name = name.strip()
        return name
