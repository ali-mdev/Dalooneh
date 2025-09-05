from django import forms
from .models import Table

class TableForm(forms.ModelForm):
    """Form for creating and editing tables"""
    
    class Meta:
        model = Table
        fields = ['number', 'seats', 'is_active']
        labels = {
            'number': 'Table Number',
            'seats': 'Capacity (Number of Seats)',
            'is_active': 'Active',
        }
        help_texts = {
            'number': 'Table number must be unique',
            'seats': 'Number of seats at the table',
            'is_active': 'If active, the table is available for ordering',
        }
        widgets = {
            'number': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'seats': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_number(self):
        """Validate table number to be unique"""
        number = self.cleaned_data['number']
        
        # Check if the table number is unique, excluding the current instance
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            # If we're editing an existing table, exclude it from the uniqueness check
            if Table.objects.exclude(pk=instance.pk).filter(number=number).exists():
                raise forms.ValidationError('A table with this number already exists')
        else:
            # If we're creating a new table, check if the number exists
            if Table.objects.filter(number=number).exists():
                raise forms.ValidationError('A table with this number already exists')
        
        return number
    
    def clean_seats(self):
        """Validate number of seats"""
        seats = self.cleaned_data['seats']
        
        # Ensure seats is at least 1
        if seats < 1:
            raise forms.ValidationError('Number of seats must be at least 1')
            
        return seats 