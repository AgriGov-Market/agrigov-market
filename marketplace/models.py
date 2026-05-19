from django.core.validators import FileExtensionValidator
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

USER_TYPE_CHOICES = (
    ('farmer', 'Farmer'),
    ('buyer', 'Buyer'),
    ('transporter', 'Transporter'),
    ('admin', 'Admin'),
)

WILAYA_CHOICES = (
    ('Adrar', 'Adrar'),
    ('Chlef', 'Chlef'),
    ('Laghouat', 'Laghouat'),
    ('Oum El Bouaghi', 'Oum El Bouaghi'),
    ('Batna', 'Batna'),
    ('Béjaïa', 'Béjaïa'),
    ('Biskra', 'Biskra'),
    ('Béchar', 'Béchar'),
    ('Blida', 'Blida'),
    ('Bouira', 'Bouira'),
    ('Tamanrasset', 'Tamanrasset'),
    ('Tébessa', 'Tébessa'),
    ('Tlemcen', 'Tlemcen'),
    ('Tiaret', 'Tiaret'),
    ('Tizi Ouzou', 'Tizi Ouzou'),
    ('Alger', 'Alger'),
    ('Djelfa', 'Djelfa'),
    ('Jijel', 'Jijel'),
    ('Sétif', 'Sétif'),
    ('Saïda', 'Saïda'),
    ('Skikda', 'Skikda'),
    ('Sidi Bel Abbès', 'Sidi Bel Abbès'),
    ('Annaba', 'Annaba'),
    ('Guelma', 'Guelma'),
    ('Constantine', 'Constantine'),
    ('Médéa', 'Médéa'),
    ('Mostaganem', 'Mostaganem'),
    ('M\'Sila', 'M\'Sila'),
    ('Mascara', 'Mascara'),
    ('Ouargla', 'Ouargla'),
    ('Oran', 'Oran'),
    ('El Bayadh', 'El Bayadh'),
    ('Illizi', 'Illizi'),
    ('Bordj Bou Arréridj', 'Bordj Bou Arréridj'),
    ('Boumerdès', 'Boumerdès'),
    ('El Tarf', 'El Tarf'),
    ('Tindouf', 'Tindouf'),
    ('Tissemsilt', 'Tissemsilt'),
    ('El Oued', 'El Oued'),
    ('Khenchela', 'Khenchela'),
    ('Souk Ahras', 'Souk Ahras'),
    ('Tipaza', 'Tipaza'),
    ('Mila', 'Mila'),
    ('Aïn Defla', 'Aïn Defla'),
    ('Naâma', 'Naâma'),
    ('Aïn Témouchent', 'Aïn Témouchent'),
    ('Ghardaïa', 'Ghardaïa'),
    ('Relizane', 'Relizane'),
)


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES)
    is_validated = models.BooleanField(default=False)
    validation_rejection_reason = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.user_type}"


class TransporterInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
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
    location = models.CharField(max_length=200, blank=True)
    street = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    wilaya = models.CharField(max_length=50, choices=WILAYA_CHOICES, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    area_hectares = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Area (hectares)", validators=[MinValueValidator(Decimal('0.01'))])
    description = models.TextField(blank=True)

    def __str__(self):
        address = self.wilaya or self.location or 'Unknown location'
        return f"{self.name} ({address})"


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )
    min_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True,
        blank=True,
        verbose_name='Minimum price range (DA/kg)',
        help_text='Minimum allowed price range for this category in DA per kg.',
    )
    max_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        null=True,
        blank=True,
        verbose_name='Maximum price range (DA/kg)',
        help_text='Maximum allowed price range for this category in DA per kg.',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['parent__name', 'name']
        verbose_name_plural = 'product categories'

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    @property
    def full_name(self):
        return str(self)


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
    farm = models.ForeignKey(
        Farm,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products',
    )
    description = models.TextField(blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg')
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    image = models.FileField(
        upload_to='products/',
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def display_name(self):
        # Display the product's own name; category is shown separately in UI
        return self.name

    def __str__(self):
        return f"{self.display_name} by {self.farmer.username}"

    @property
    def image_urls(self):
        urls = [img.image.url for img in self.images.all() if img.image]
        if self.image and self.image.url not in urls:
            urls.insert(0, self.image.url)
        return urls

    @property
    def first_image_url(self):
        first_image = self.images.first()
        if first_image and first_image.image:
            return first_image.image.url
        if self.image:
            try:
                return self.image.url
            except Exception:
                return None
        return None


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.FileField(
        upload_to='product_images/',
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])],
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Image for {self.product.display_name}"


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
    quantity = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    total_price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_address = models.TextField()
    rejection_reason = models.TextField(blank=True)

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
    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('200.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )

    def __str__(self):
        return f"Delivery for Order #{self.order.id}"


class OfficialPrice(models.Model):
    commodity = models.CharField(max_length=100)
    price_per_kg = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    effective_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.commodity}: DA {self.price_per_kg}/kg"


class Rating(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ratings')
    rater = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    rated_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_received')
    score = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('order', 'rater', 'rated_user')
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.rater.username} rated {self.rated_user.username}: {self.score}/5"


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='wishlist_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} -> {self.product.display_name}"


class DismissedNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dismissed_notifications')
    notification_id = models.CharField(max_length=50)
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'notification_id')
        ordering = ['-dismissed_at']

    def __str__(self):
        return f"{self.user.username} dismissed {self.notification_id}"


class UserNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_notifications')
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    url = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"
