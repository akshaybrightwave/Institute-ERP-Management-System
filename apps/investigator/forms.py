from django import forms

from .models import FraudType, PoliceStation


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
