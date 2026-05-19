from django import forms
from decimal import Decimal
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import USER_TYPE_CHOICES, WILAYA_CHOICES, UserProfile, TransporterInfo, Farm, Product, Order, Delivery, OfficialPrice, ProductCategory, Rating

class RegisterForm(UserCreationForm):
    user_type = forms.ChoiceField(choices=USER_TYPE_CHOICES, label="Account type")
    phone = forms.CharField(max_length=15, required=True)
    address = forms.CharField(widget=forms.Textarea, required=True)
    capacity_kg = forms.DecimalField(
        max_digits=10, decimal_places=2, required=False,
        label="Vehicle capacity (KG)", help_text="Required for transporters",
        min_value=Decimal('0.01')
    )
    vehicle_number = forms.CharField(max_length=50, required=False, label="Vehicle number")

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'user_type', 'phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user_type'].choices = [choice for choice in USER_TYPE_CHOICES if choice[0] != 'admin']
        self.fields['email'].required = True

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        capacity_kg = cleaned_data.get('capacity_kg')
        vehicle_number = cleaned_data.get('vehicle_number')

        if user_type == 'transporter':
            if not capacity_kg:
                self.add_error('capacity_kg', 'Capacity in KG is required for transporters.')
            if not vehicle_number:
                self.add_error('vehicle_number', 'Vehicle number is required for transporters.')

        return cleaned_data

class FarmForm(forms.ModelForm):
    class Meta:
        model = Farm
        fields = ['name', 'street', 'city', 'wilaya', 'postal_code', 'location', 'area_hectares', 'description']
        widgets = {
            'street': forms.TextInput(attrs={'placeholder': 'Street address'}),
            'city': forms.TextInput(attrs={'placeholder': 'City'}),
            'wilaya': forms.Select(attrs={'class': 'form-select'}),
            'postal_code': forms.TextInput(attrs={'placeholder': 'Postal code (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area_hectares'].min_value = Decimal('0.01')
        for name in ['name', 'street', 'city', 'postal_code', 'location', 'area_hectares', 'description']:
            self.fields[name].widget.attrs.update({'class': 'form-control'})
        self.fields['wilaya'].widget.attrs.update({'class': 'form-select'})

class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleImageField(forms.FileField):
    widget = MultipleImageInput

    def clean(self, data, initial=None):
        if not data:
            return []
        if isinstance(data, list):
            cleaned_files = []
            for uploaded_file in data:
                if uploaded_file:
                    cleaned_files.append(super().clean(uploaded_file, initial))
            return cleaned_files
        return [super().clean(data, initial)]


class ProductForm(forms.ModelForm):
    main_category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(parent__isnull=True, is_active=True).order_by('name'),
        empty_label='Select a main category',
        required=True,
        label='Category',
    )
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True).order_by('parent__name', 'name'),
        empty_label='Select a subcategory',
        required=True,
        label='Subcategory',
    )
    images = MultipleImageField(
        widget=MultipleImageInput(attrs={'accept': 'image/*', 'multiple': True}),
        required=False,
        label='Product Images',
        help_text='Upload one or more product photos (JPEG, PNG, WEBP).',
    )

    class Meta:
        model = Product
        fields = ['name', 'main_category', 'category', 'farm', 'description', 'quantity', 'unit', 'price_per_unit']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.farmer = kwargs.pop('farmer', None)
        super().__init__(*args, **kwargs)
        self.fields['quantity'].min_value = Decimal('0.01')
        self.fields['price_per_unit'].min_value = Decimal('0.01')
        self.fields['name'].label = "Product Name"
        self.fields['farm'].required = False
        self.fields['farm'].queryset = Farm.objects.filter(farmer=self.farmer) if self.farmer else Farm.objects.none()
        self.fields['farm'].empty_label = "Select farm"
        self.fields['main_category'].widget.attrs.update({'class': 'form-select'})
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['farm'].widget.attrs.update({'class': 'form-select'})
        self.fields['unit'].widget.attrs.update({'class': 'form-select'})
        self.fields['images'].widget.attrs.update({'class': 'form-control'})
        for name in ['name', 'quantity', 'price_per_unit', 'description']:
            self.fields[name].widget.attrs.update({'class': 'form-control'})
        self.fields['price_per_unit'].help_text = "This price must fall within the approved category/subcategory range or the current official market range."

        if self.instance and self.instance.pk and self.instance.category:
            self.fields['main_category'].initial = self.instance.category.parent or self.instance.category

    def clean(self):
        cleaned_data = super().clean()
        main_category = cleaned_data.get('main_category')
        category = cleaned_data.get('category')
        if main_category and category:
            if category != main_category and category.parent != main_category:
                self.add_error('category', 'Please select a valid subcategory for the chosen main category.')
        return cleaned_data

    def _official_price_range(self, category, unit):
        if not category:
            return None

        current_category = category
        while current_category is not None:
            if current_category.min_price is not None and current_category.max_price is not None:
                min_price = current_category.min_price
                max_price = current_category.max_price
                return min_price, max_price, current_category
            current_category = current_category.parent

        lookup_category = category
        official_price = None
        while lookup_category is not None and official_price is None:
            official_price = OfficialPrice.objects.filter(commodity__iexact=lookup_category.name).order_by('-effective_date', '-id').first()
            lookup_category = lookup_category.parent

        if not official_price:
            return None

        base_price = official_price.price_per_kg
        if unit == 'ton':
            base_price = base_price * Decimal('1000')
        min_price = (base_price * Decimal('0.80')).quantize(Decimal('0.01'))
        max_price = (base_price * Decimal('1.20')).quantize(Decimal('0.01'))
        return min_price, max_price, official_price

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        unit = cleaned_data.get('unit')
        price = cleaned_data.get('price_per_unit')
        price_range = self._official_price_range(category, unit)
        if price and price_range:
            min_price, max_price, source = price_range
            if price < min_price or price > max_price:
                label = category.name if isinstance(source, ProductCategory) else category.name
                if isinstance(source, ProductCategory):
                    self.add_error(
                        'price_per_unit',
                        f"Price must be between DA {min_price} and DA {max_price} for {source.name} based on the configured category range.",
                    )
                else:
                    self.add_error(
                        'price_per_unit',
                        f"Price must be between DA {min_price} and DA {max_price} for {label} based on the official price of DA {source.price_per_kg}/kg.",
                    )
        return cleaned_data


class ProductCategoryForm(forms.ModelForm):
    parent = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True).order_by('name'),
        required=False,
        label='Parent Category',
        empty_label='No parent (top-level category)',
    )

    class Meta:
        model = ProductCategory
        fields = ['name', 'parent', 'min_price', 'max_price', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'min_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parent'].widget.attrs.update({'class': 'form-select'})
        self.fields['min_price'].required = False
        self.fields['max_price'].required = False
        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = ProductCategory.objects.filter(is_active=True).exclude(id=self.instance.id).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        if (min_price is None) ^ (max_price is None):
            raise forms.ValidationError('Please provide both minimum and maximum price values, or leave both blank.')
        if min_price is not None and max_price is not None and min_price > max_price:
            raise forms.ValidationError('Minimum price must be less than or equal to maximum price.')
        return cleaned_data

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['quantity', 'delivery_address']
        widgets = {
            'delivery_address': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Street, City, Wilaya, Postal Code',
            }),
        }

    def __init__(self, *args, **kwargs):
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        self.fields['delivery_address'].widget.attrs.update({'class': 'form-control'})
        # ensure quantity input is styled and has reasonable step/min attributes
        self.fields['quantity'].widget.attrs.update({'class': 'form-control', 'min': '0.01', 'step': '0.01'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity is not None and quantity <= 0:
            raise forms.ValidationError("Quantity must be greater than zero.")
        if self.product and quantity > self.product.quantity:
            raise forms.ValidationError(f"Only {self.product.quantity} {self.product.unit} available.")
        return quantity

class DeliveryForm(forms.ModelForm):
    delivery_status = forms.ChoiceField(choices=[
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ])

    class Meta:
        model = Delivery
        fields = ['estimated_delivery_date', 'actual_delivery_date', 'delivery_status']
        widgets = {
            'estimated_delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'actual_delivery_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class DeliveryFeeForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['delivery_fee']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_fee'].min_value = Decimal('0.01')
        self.fields['delivery_fee'].widget.attrs.update({'class': 'form-control'})


class UserAccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['phone', 'address']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class TransporterInfoForm(forms.ModelForm):
    class Meta:
        model = TransporterInfo
        fields = ['capacity_kg', 'vehicle_number']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})
        self.fields['capacity_kg'].min_value = Decimal('0.01')

class OfficialPriceForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ProductCategory.objects.filter(is_active=True).order_by('parent__name', 'name'),
        empty_label='Select a ministry-approved category',
    )

    class Meta:
        model = OfficialPrice
        fields = ['price_per_kg']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['price_per_kg'].min_value = 0
        self.fields['price_per_kg'].min_value = Decimal('0.01')
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['price_per_kg'].widget.attrs.update({'class': 'form-control'})
        if self.instance and self.instance.pk:
            self.fields['category'].initial = ProductCategory.objects.filter(name__iexact=self.instance.commodity).first()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.commodity = self.cleaned_data['category'].name
        if commit:
            instance.save()
        return instance


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['score', 'comment']
        widgets = {
            'score': forms.Select(choices=[(5, '5 - Excellent'), (4, '4 - Good'), (3, '3 - Fair'), (2, '2 - Poor'), (1, '1 - Bad')]),
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional feedback'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['score'].widget.attrs.update({'class': 'form-select form-select-sm'})
        self.fields['comment'].widget.attrs.update({'class': 'form-control form-control-sm'})
