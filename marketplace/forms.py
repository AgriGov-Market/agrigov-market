from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import USER_TYPE_CHOICES, Farm, Product, Order, Delivery, OfficialPrice, ProductCategory

class RegisterForm(UserCreationForm):
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label="Account type")
    phone = forms.CharField(max_length=15, required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    capacity_kg = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Vehicle capacity (KG)", help_text="Required for transporters",
        min_value=0
    )
    vehicle_number = forms.CharField(max_length=50, required=False, label="Vehicle number")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'user_type', 'phone', 'address']

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        capacity_kg = cleaned_data.get('capacity_kg')

        if user_type == 'transporter' and not capacity_kg:
            self.add_error('capacity_kg', 'Capacity in KG is required for transporters.')
        return cleaned_data

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'location', 'size_acres']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['size_acres'].min_value = 0

class ProductForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True).order_by('name'),
        empty_label='Select a ministry-approved category',
    )

    class Meta:
        model = Product
        fields = ['category', 'image', 'quantity', 'unit', 'price_per_unit']
        widgets = {
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['quantity'].min_value = 0
        self.fields['price_per_unit'].min_value = 0


class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name']

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['quantity', 'delivery_address']

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if self.product and quantity > self.product.quantity:
            raise forms.ValidationError(f"Only {self.product.quantity} {self.product.unit} available.")
        return quantity

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['estimated_delivery_date', 'actual_delivery_date', 'delivery_status']
        widgets = {
            'estimated_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }

class OfficialPriceForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True).order_by('name'),
        empty_label='Select a ministry-approved category',
    )

    class Meta:
        model = OfficialPrice
        fields = ['price_per_kg']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price_per_kg'].min_value = 0

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.commodity = self.cleaned_data['category'].name
        if commit:
            instance.save()
        return instance
