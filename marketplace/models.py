from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

# User Profile extending Django's User
class Profile(models.Model):
    ROLE_CHOICES = [
        ('farmer', 'Farmer'),
        ('buyer', 'Buyer'),
        ('transporter', 'Transporter'),
        ('admin', 'Ministry Admin'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='buyer')
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user.username} - {self.role}"

# Farm model (for farmers)
class Farm(models.Model):
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='farms')
    name = models.CharField(max_length=100)
    location = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

# Product model
class Product(models.Model):
    QUALITY_CHOICES = [
        ('A', 'Premium'),
        ('B', 'Standard'),
        ('C', 'Economy'),
    ]
    
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=20, default='kg')
    quality = models.CharField(max_length=1, choices=QUALITY_CHOICES, default='B')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.farmer.username}"

# Order model
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_buyer')
    farmer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_as_farmer')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.TextField()
    
    def __str__(self):
        return f"Order #{self.id} - {self.buyer.username}"

# Delivery model (for transporters)
class Delivery(models.Model):
    STATUS_CHOICES = [
        ('assigned', 'Assigned'),
        ('picked_up', 'Picked Up'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]
    
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
    transporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='deliveries', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    pickup_location = models.CharField(max_length=200)
    dropoff_location = models.CharField(max_length=200)
    estimated_days = models.IntegerField(default=3)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Delivery for Order #{self.order.id}"

# Transporter profile extension
class TransporterInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='transporter_info')
    vehicle_type = models.CharField(max_length=50)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2)
    service_areas = models.TextField()
    is_available = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.vehicle_type}"

# Auto-create Profile when User is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()