from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import Product, Farm, Delivery

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()
    role = forms.ChoiceField(choices=[('farmer', 'Farmer'), ('buyer', 'Buyer'), ('transporter', 'Transporter')])
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    vehicle_type = forms.CharField(max_length=50, required=False)
    capacity_kg = forms.DecimalField(max_digits=10, decimal_places=2, required=False)
    service_areas = forms.CharField(widget=forms.Textarea, required=False)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'role', 'phone', 'address']

class UserLoginForm(AuthenticationForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['farm', 'name', 'category', 'quantity', 'unit', 'quality', 'price_per_unit', 'available']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.TextInput(attrs={'class': 'form-control'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_per_unit': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'location', 'description']

class DeliveryStatusForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['status']