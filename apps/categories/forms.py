from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):
    name = forms.CharField(
        max_length=255,
        strip=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter category name',
            'autofocus': True,
        }),
        error_messages={
            'required': 'Category name is required.',
            'max_length': 'Category name cannot exceed 255 characters.',
        }
    )

    class Meta:
        model = Category
        fields = ['name']

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Category name is required.')
        
        if self.instance and self.instance.pk:
            # On Edit: Check all categories (active or deleted) to prevent duplicate constraint violation
            qs = Category.all_objects.filter(name__iexact=name).exclude(pk=self.instance.pk)
        else:
            # On Creation: Only check active categories. Soft-deleted ones will be restored on save.
            qs = Category.objects.filter(name__iexact=name)
            
        if qs.exists():
            raise forms.ValidationError('Category already exists.')
        return name

    def save(self, commit=True):
        name = self.cleaned_data.get('name', '').strip()
        if not self.instance.pk:
            # Look for a soft-deleted category with this name to restore
            soft_deleted = Category.all_objects.filter(is_deleted=True, name__iexact=name).first()
            if soft_deleted:
                soft_deleted.restore()
                self.instance = soft_deleted
                return self.instance
        return super().save(commit=commit)
