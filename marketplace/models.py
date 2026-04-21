from django.core.validators import FileExtensionValidator
from django.db import models
from django.contrib.auth.models import User

USER_TYPE_CHOICES = (
    ('farmer', 'Farmer'),
    ('buyer', 'Buyer'),
    ('transporter', 'Transporter'),
    ('admin', 'Admin'),
)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class TransporterInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    vehicle_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.capacity_kg} kg"


class Farm(models.Model):
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'userprofile__user_type': 'farmer'},
    )
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    size_acres = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'product categories'

    def __str__(self):
        return self.name


class Product(models.Model):
    UNIT_CHOICES = (('kg', 'Kilogram'), ('ton', 'Ton'), ('piece', 'Piece'))
    farmer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'userprofile__user_type': 'farmer'},
    )
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='products',
    )
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.FileField(
        upload_to='products/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def display_name(self):
        return self.category.name if self.category else self.name

    def __str__(self):
        return f"{self.display_name} by {self.farmer.username}"


class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.TextField()

    def __str__(self):
        return f"Order #{self.id} - {self.product.display_name}"


class Delivery(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    transporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'userprofile__user_type': 'transporter'},
    )
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateField(null=True, blank=True)
    delivery_status = models.CharField(max_length=20, default='pending')

    def __str__(self):
        return f"Delivery for Order #{self.order.id}"


class OfficialPrice(models.Model):
    commodity = models.CharField(max_length=100)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2)
    effective_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.commodity}: DA {self.price_per_kg}/kg"
