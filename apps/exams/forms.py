from django import forms
from .models import Exam, Option, Question, ExamSchedule


from django.db.models import Q
from apps.centers.models import Center
from apps.courses.models import Course

class ExamForm(forms.ModelForm):
    center = forms.ModelChoiceField(
        queryset=Center.objects.all(),
        required=False,
        empty_label="Select a Center (Global if blank)",
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_center'})
    )
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        required=True,
        empty_label="Select a Course",
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_course'})
    )
    course_duration = forms.ChoiceField(
        choices=[('', 'Select Course Duration')],
        required=True,
        widget=forms.Select(attrs={'class': 'form-select dark-input', 'id': 'id_course_duration'})
    )
    start_datetime = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control dark-input', 'id': 'id_start_datetime'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    end_datetime = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control dark-input', 'id': 'id_end_datetime'}),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Exam
        fields = [
            'title', 'description', 'center', 'course', 'course_duration',
            'total_questions', 'start_datetime', 'end_datetime', 'duration_minutes', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control text-white dark-input', 'placeholder': 'Enter Exam Title', 'id': 'id_title'}),
            'description': forms.Textarea(attrs={'class': 'form-control text-white dark-input', 'rows': 3, 'placeholder': 'Enter Exam Description', 'id': 'id_description'}),
            'total_questions': forms.NumberInput(attrs={'class': 'form-control text-white dark-input', 'min': 1, 'placeholder': 'Maximum Questions', 'id': 'id_total_questions'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control text-white dark-input', 'min': 1, 'placeholder': 'Duration (minutes)', 'id': 'id_duration_minutes'}),
            'is_published': forms.CheckboxInput(attrs={'class': 'form-check-input ms-2', 'id': 'id_is_published'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.user:
            if self.user.role == 'center':
                user_center = self.user.center
                self.fields['center'].queryset = Center.objects.filter(id=user_center.id)
                self.fields['center'].initial = user_center
                self.fields['center'].widget.attrs.update({'disabled': 'disabled'})
                
                # Only show courses assigned to the logged-in center via CenterCourseAssignment
                self.fields['course'].queryset = Course.objects.filter(
                    assignments__center=user_center,
                    assignments__is_active=True
                ).distinct().order_by('name')

                # Re-label description as Message and make required
                self.fields['description'].label = "Message"
                self.fields['description'].required = True
                self.fields['description'].widget.attrs.update({
                    'placeholder': 'Enter Message',
                    'rows': 4
                })

                # Make admin-only fields optional for Center request submission
                self.fields['title'].required = False
                self.fields['course_duration'].required = False
                self.fields['start_datetime'].required = False
                self.fields['end_datetime'].required = False
                self.fields['total_questions'].required = False
                self.fields['duration_minutes'].required = False
                self.fields['center'].required = False
            else:
                self.fields['center'].queryset = Center.objects.all().order_by('name')
                self.fields['course'].queryset = Course.objects.all().order_by('name')

        # Handle post or editing setup for courses and course duration
        center_id = None
        course_id = None
        if self.is_bound:
            center_id = self.data.get('center')
            course_id = self.data.get('course')
        elif self.instance and self.instance.pk:
            center_id = self.instance.center.id if self.instance.center else None
            course_id = self.instance.course.id if self.instance.course else None

        if self.user and self.user.role == 'center':
            center_id = self.user.center.id

        if center_id:
            if self.user and self.user.role == 'center':
                self.fields['course'].queryset = Course.objects.filter(
                    assignments__center_id=center_id,
                    assignments__is_active=True
                ).distinct().order_by('name')
            else:
                self.fields['course'].queryset = Course.objects.filter(
                    Q(center_id=center_id) | Q(center__isnull=True)
                ).order_by('name')
        
        if course_id:
            try:
                course_obj = Course.objects.get(id=course_id)
                from apps.results.forms import ResultForm
                temp_form = ResultForm()
                choices = temp_form._parse_duration_choices(course_obj.duration)
                self.fields['course_duration'].choices = [('', 'Select Course Duration')] + [(c, c) for c in choices]
            except Course.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        course_duration = cleaned_data.get('course_duration')
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        total_questions = cleaned_data.get('total_questions')
        duration_minutes = cleaned_data.get('duration_minutes')

        if self.user and self.user.role == 'center':
            cleaned_data['center'] = self.user.center
            
            # Server-side validation that selected course belongs to the center
            if course:
                if not Course.objects.filter(
                    id=course.id,
                    assignments__center=self.user.center,
                    assignments__is_active=True
                ).exists():
                    self.add_error('course', "Selected Course is not assigned to your Center.")

            # Automatically populate default values for required fields
            if course:
                cleaned_data['title'] = f"Exam Request - {course.name}"
            cleaned_data['is_published'] = False
            from django.utils.timezone import now
            cleaned_data['start_datetime'] = now()
            cleaned_data['date'] = now().date()

        else:
            if total_questions is not None and total_questions <= 0:
                self.add_error('total_questions', "Maximum Questions must be greater than zero.")

            if duration_minutes is not None and duration_minutes <= 0:
                self.add_error('duration_minutes', "Exam Timer must be greater than zero.")

            if start_datetime and end_datetime:
                if start_datetime >= end_datetime:
                    self.add_error('start_datetime', "Start DateTime must be before End DateTime.")
                    self.add_error('end_datetime', "End DateTime must be after Start DateTime.")

            # Duplicate check: Course + Course Duration + Same Start DateTime
            if course and course_duration and start_datetime:
                dup_qs = Exam.objects.filter(
                    course=course,
                    course_duration=course_duration,
                    start_datetime=start_datetime
                )
                if self.instance and self.instance.pk:
                    dup_qs = dup_qs.exclude(pk=self.instance.pk)
                if dup_qs.exists():
                    raise forms.ValidationError("An exam with this Course, Duration, and Start Date/Time already exists.")

        return cleaned_data


class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['question_text', 'marks']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'marks': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class OptionForm(forms.ModelForm):
    class Meta:
        model = Option
        fields = ['text', 'is_correct']
        widgets = {
            'text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter option text'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ExamScheduleForm(forms.ModelForm):
    duration = forms.ChoiceField(
        choices=[
            ('', 'Select duration'),
            ('1 Month', '1 Month'),
            ('2 Months', '2 Months'),
            ('3 Months', '3 Months'),
            ('6 Months', '6 Months'),
            ('1 Year', '1 Year'),
            ('2 Years', '2 Years'),
        ],
        widget=forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'})
    )

    class Meta:
        model = ExamSchedule
        fields = ['center', 'course', 'duration', 'exam_center', 'session']
        widgets = {
            'center': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'course': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'exam_center': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
            'session': forms.Select(attrs={'class': 'form-control dark-input', 'style': 'background-color: var(--erp-bg-input); border: 1px solid var(--erp-border-input); border-radius: 8px; color: #fff;'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['center'].empty_label = "Select a Center"
        self.fields['course'].empty_label = "Select a Course"
        self.fields['exam_center'].empty_label = "Select Exam Centre"
        self.fields['session'].empty_label = "Select Session"

    # NOTE: StudentProfileForm → apps/students/forms.py
    #       TeacherProfileForm → apps/teachers/forms.py
