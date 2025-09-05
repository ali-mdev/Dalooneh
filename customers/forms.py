from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Customer, CustomerRating, Discount

class CustomerRegistrationForm(UserCreationForm):
    phone_number = forms.CharField(max_length=15, required=True)
    national_code = forms.CharField(max_length=10, required=False, label='National ID')
    birth_date = forms.DateField(required=True, widget=forms.DateInput(attrs={'type': 'date'}))
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')

class CustomerProfileForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ('phone_number', 'address', 'national_code', 'birth_date')
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }

class CustomerRatingForm(forms.ModelForm):
    class Meta:
        model = CustomerRating
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'class': 'form-control'
            }),
            'comment': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Write your comments about the order...'
            })
        }
    
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating < 1 or rating > 5:
            raise forms.ValidationError('Rating must be between 1 and 5.')
        return rating

# Management Panel Forms
class ManagementCustomerForm(forms.ModelForm):
    first_name = forms.CharField(max_length=30, required=True, label='First Name')
    last_name = forms.CharField(max_length=30, required=True, label='Last Name')
    email = forms.EmailField(required=False, label='Email')
    
    class Meta:
        model = Customer
        fields = ('phone_number', 'national_code', 'address', 'birth_date', 'membership_level', 'is_active')
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
            'national_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'National ID'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Address', 'rows': 3}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'membership_level': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance', None)
        if instance:
            initial = kwargs.get('initial', {})
            initial['first_name'] = instance.user.first_name
            initial['last_name'] = instance.user.last_name
            initial['email'] = instance.user.email
            kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        customer = super().save(commit=False)
        if commit:
            # Save related User model data
            customer.user.first_name = self.cleaned_data['first_name']
            customer.user.last_name = self.cleaned_data['last_name']
            customer.user.email = self.cleaned_data['email']
            customer.user.save()
            customer.save()
        return customer

class ManagementCustomerRatingForm(forms.ModelForm):
    class Meta:
        model = CustomerRating
        fields = ('customer', 'order', 'rating', 'comment')
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'rating': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ManagementDiscountForm(forms.ModelForm):
    class Meta:
        model = Discount
        fields = ('customer', 'code', 'percentage', 'is_active', 'valid_from', 'valid_to')
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Discount Code'}),
            'percentage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Discount Percentage', 'min': 1, 'max': 100}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_to': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        } 