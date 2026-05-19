from django.contrib import admin
from django.utils.html import format_html
from .models import Product, ProductImage, Farm, UserProfile, Delivery, ProductCategory, Order, Rating, WishlistItem, OfficialPrice, TransporterInfo

# Inline admin for ProductImage
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ('image', 'id')
    readonly_fields = ('id',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'farmer', 'category', 'price_per_unit', 'quantity', 'available_status', 'created_at')
    list_filter = ('category', 'available', 'created_at', 'farmer')
    search_fields = ('name', 'description', 'farmer__username')
    readonly_fields = ('created_at',)
    inlines = [ProductImageInline]
    actions = ['delete_selected_products', 'mark_available', 'mark_unavailable']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'farmer', 'farm')
        }),
        ('Details', {
            'fields': ('description', 'quantity', 'unit', 'price_per_unit')
        }),
        ('Status', {
            'fields': ('available',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def available_status(self, obj):
        if obj.available:
            return format_html('<span style="color: green; font-weight: bold;">✓ Available</span>')
        return format_html('<span style="color: red; font-weight: bold;">✗ Not Available</span>')
    available_status.short_description = 'Status'
    
    def delete_selected_products(self, request, queryset):
        count = queryset.count()
        queryset.delete()
        self.message_user(request, f"✓ Successfully deleted {count} product(s)")
    delete_selected_products.short_description = "🗑️ Delete selected products"
    
    def mark_available(self, request, queryset):
        count = queryset.update(available=True)
        self.message_user(request, f"✓ Marked {count} product(s) as available")
    mark_available.short_description = "✓ Mark selected as available"
    
    def mark_unavailable(self, request, queryset):
        count = queryset.update(available=False)
        self.message_user(request, f"✗ Marked {count} product(s) as unavailable")
    mark_unavailable.short_description = "✗ Mark selected as unavailable"


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('product', 'image_preview', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('product__name',)
    readonly_fields = ('image_preview_large', 'uploaded_at')
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 4px;" />', obj.image.url)
        return "No image"
    image_preview.short_description = 'Preview'
    
    def image_preview_large(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-width: 300px; border-radius: 8px;" />', obj.image.url)
        return "No image"
    image_preview_large.short_description = 'Image Preview'


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = ('name', 'farmer', 'city', 'wilaya', 'area_hectares')
    list_filter = ('wilaya', 'city')
    search_fields = ('name', 'farmer__username', 'city')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'farmer', 'description')
        }),
        ('Location', {
            'fields': ('street', 'city', 'wilaya', 'postal_code', 'location')
        }),
        ('Details', {
            'fields': ('area_hectares',)
        }),
    )


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'transporter', 'status_badge', 'created_at')
    list_filter = ('delivery_status', 'order__order_date')
    search_fields = ('order__id', 'transporter__username')
    readonly_fields = ('order',)
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'confirmed': '#1E90FF',
            'shipped': '#9370DB',
            'delivered': '#228B22',
            'cancelled': '#DC143C',
            'rejected': '#8B0000'
        }
        color = colors.get(obj.delivery_status, '#808080')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.delivery_status.title()
        )
    status_badge.short_description = 'Status'
    
    def created_at(self, obj):
        return obj.order.order_date
    created_at.short_description = 'Created'


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'parent_name', 'price_range', 'is_active', 'product_count')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'parent__name')
    fields = ('name', 'parent', 'is_active', 'min_price', 'max_price')

    def parent_name(self, obj):
        return obj.parent.name if obj.parent else '-'
    parent_name.short_description = 'Parent'

    def price_range(self, obj):
        if obj.min_price is not None and obj.max_price is not None:
            return format_html('DA {} - DA {}/kg', obj.min_price, obj.max_price)
        return 'Not set'
    price_range.short_description = 'Price Range'

    def product_count(self, obj):
        count = obj.products.count()
        return format_html('<strong>{}</strong>', count)
    product_count.short_description = 'Products'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'product', 'quantity', 'total_price', 'status_badge', 'order_date')
    list_filter = ('status', 'order_date', 'buyer')
    search_fields = ('buyer__username', 'product__name', 'id')
    readonly_fields = ('order_date',)
    
    fieldsets = (
        ('Order Information', {
            'fields': ('buyer', 'product', 'quantity', 'total_price')
        }),
        ('Delivery', {
            'fields': ('delivery_address', 'status')
        }),
        ('Rejection', {
            'fields': ('rejection_reason',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('order_date',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'pending': '#FFA500',
            'confirmed': '#1E90FF',
            'shipped': '#9370DB',
            'delivered': '#228B22',
            'cancelled': '#DC143C',
        }
        color = colors.get(obj.status, '#808080')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 4px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'user_type', 'phone', 'is_validated')
    list_filter = ('user_type', 'is_validated')
    search_fields = ('user__username', 'phone')
    readonly_fields = ('user',)
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'user_type')
        }),
        ('Contact', {
            'fields': ('phone', 'address')
        }),
        ('Validation', {
            'fields': ('is_validated', 'validation_rejection_reason')
        }),
    )


@admin.register(TransporterInfo)
class TransporterInfoAdmin(admin.ModelAdmin):
    list_display = ('user', 'capacity_kg', 'vehicle_number')
    search_fields = ('user__username', 'vehicle_number')
    readonly_fields = ('user',)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('rater', 'rated_user', 'score_stars', 'created_at')
    list_filter = ('score', 'created_at')
    search_fields = ('rater__username', 'rated_user__username')
    readonly_fields = ('created_at', 'updated_at')
    
    def score_stars(self, obj):
        stars = '⭐' * obj.score
        return format_html('{} <strong>({})</strong>', stars, obj.score)
    score_stars.short_description = 'Rating'


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'product__name')
    readonly_fields = ('created_at',)


@admin.register(OfficialPrice)
class OfficialPriceAdmin(admin.ModelAdmin):
    list_display = ('commodity', 'price_per_kg', 'effective_date')
    list_filter = ('effective_date',)
    search_fields = ('commodity',)
    readonly_fields = ('effective_date',)
