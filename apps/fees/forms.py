from django import forms
from .models import CenterPaymentSetting, FeePayment, StudentPaymentSetting
from apps.students.models import StudentProfile


class FeePaymentForm(forms.ModelForm):
    class Meta:
        model = FeePayment
        fields = ['student', 'amount', 'payment_date', 'payment_method', 'reference_number', 'remarks']
        widgets = {
            'student': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'payment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'payment_method': forms.Select(attrs={'class': 'form-select'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Prepopulate with today's date if not set
        from datetime import date
        if not self.initial.get('payment_date'):
            self.initial['payment_date'] = date.today()
            
        # Restrict student selection based on user role/center
        if self.user and self.user.role == 'center':
            self.fields['student'].queryset = StudentProfile.objects.filter(
                batch__center=self.user.center
            ).order_by('full_name')
        else:
            self.fields['student'].queryset = StudentProfile.objects.all().order_by('full_name')

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get('student')
        amount = cleaned_data.get('amount')

        if student and amount is not None:
            # Check center isolation
            if self.user and self.user.role == 'center':
                if not student.batch or not student.batch.course or student.batch.center != self.user.center:
                    raise forms.ValidationError("Student must belong to your assigned center.")

            # Validate overpayment: Amount Paid cannot exceed Remaining Balance
            from django.db.models import Sum
            from decimal import Decimal

            course_fee = student.batch.course.fees if (student.batch and student.batch.course) else Decimal('0.00')

            other_payments = FeePayment.objects.filter(student=student)
            if self.instance and self.instance.pk:
                other_payments = other_payments.exclude(pk=self.instance.pk)

            paid_so_far = other_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
            remaining_balance = course_fee - paid_so_far

            if amount > remaining_balance:
                raise forms.ValidationError(
                    f"Overpayment is not allowed. Remaining balance is ₹{remaining_balance:.2f}, but you entered ₹{amount:.2f}."
                )

        return cleaned_data


class CenterPaymentSettingForm(forms.ModelForm):
    class Meta:
        model = CenterPaymentSetting
        fields = ['amount', 'is_visible']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control dark-input text-white center-payment-amount',
                'min': '0',
                'step': '0.01',
                'required': 'required',
            }),
            'is_visible': forms.CheckboxInput(attrs={
                'class': 'form-check-input center-payment-status',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError("Amount is required.")
        if amount < 0:
            raise forms.ValidationError("Amount cannot be negative.")
        return amount


class StudentPaymentSettingForm(forms.ModelForm):
    class Meta:
        model = StudentPaymentSetting
        fields = ['amount', 'is_visible']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class': 'form-control dark-input text-white student-payment-amount',
                'min': '0',
                'step': '0.01',
                'required': 'required',
            }),
            'is_visible': forms.CheckboxInput(attrs={
                'class': 'form-check-input student-payment-status',
            }),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is None:
            raise forms.ValidationError("Amount is required.")
        if amount < 0:
            raise forms.ValidationError("Amount cannot be negative.")
        return amount
