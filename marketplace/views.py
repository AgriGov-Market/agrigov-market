from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Sum, Count
from .models import Profile, Farm, Product, Order, Delivery, TransporterInfo
from .forms import UserRegisterForm, UserLoginForm, ProductForm, FarmForm, DeliveryStatusForm

# Home page
def home(request):
    products = Product.objects.filter(available=True)[:12]
    return render(request, 'marketplace/home.html', {'products': products})

# Logout
def user_logout(request):
    logout(request)
    return redirect('login')

# Register with AUTO-APPROVE and AUTO-LOGIN
def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            profile = user.profile
            profile.role = form.cleaned_data.get('role')
            profile.phone = form.cleaned_data.get('phone')
            profile.address = form.cleaned_data.get('address')
            profile.is_approved = True  # AUTO-APPROVE - no admin needed
            profile.save()
            
            # If transporter, create TransporterInfo
            if profile.role == 'transporter':
                TransporterInfo.objects.create(
                    user=user,
                    vehicle_type=form.cleaned_data.get('vehicle_type', 'Truck'),
                    capacity_kg=form.cleaned_data.get('capacity_kg', 1000),
                    service_areas=form.cleaned_data.get('service_areas', 'Local area')
                )
            
            # AUTO-LOGIN after registration
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to AgriGov Market.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegisterForm()
    return render(request, 'marketplace/register.html', {'form': form})

# Login with error messages
def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.profile.is_approved or user.is_superuser:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Your account is pending admin approval. Please wait for an admin to approve your account.')
                    return redirect('login')
            else:
                messages.error(request, 'Invalid username or password. Please try again.')
        else:
            messages.error(request, 'Please enter a valid username and password.')
    else:
        form = UserLoginForm()
    return render(request, 'marketplace/login.html', {'form': form})

# Dashboard (role-based)
@login_required
def dashboard(request):
    user = request.user
    role = user.profile.role
    
    context = {}
    
    if role == 'farmer':
        products = Product.objects.filter(farmer=user)
        orders = Order.objects.filter(farmer=user)
        farms = Farm.objects.filter(farmer=user)
        context = {'products': products, 'orders': orders, 'farms': farms}
        template = 'marketplace/farmer_dashboard.html'
    
    elif role == 'buyer':
        orders = Order.objects.filter(buyer=user)
        products = Product.objects.filter(available=True)
        context = {'orders': orders, 'products': products}
        template = 'marketplace/buyer_dashboard.html'
    
    elif role == 'transporter':
        deliveries = Delivery.objects.filter(transporter=user)
        available_deliveries = Delivery.objects.filter(transporter__isnull=True, status='assigned')
        context = {'deliveries': deliveries, 'available_deliveries': available_deliveries}
        template = 'marketplace/transporter_dashboard.html'
    
    else:  # admin
        pending_users = Profile.objects.filter(is_approved=False).exclude(user__is_superuser=True)
        all_products = Product.objects.all()
        all_orders = Order.objects.all()
        stats = {
            'total_users': User.objects.count(),
            'total_products': Product.objects.count(),
            'total_orders': Order.objects.count(),
            'total_revenue': Order.objects.filter(status='delivered').aggregate(Sum('total_price'))['total_price__sum'] or 0,
        }
        context = {'pending_users': pending_users, 'all_products': all_products, 'all_orders': all_orders, 'stats': stats}
        template = 'marketplace/admin_dashboard.html'
    
    return render(request, template, context)

# Product management
@login_required
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()
            messages.success(request, 'Product added successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProductForm()
    return render(request, 'marketplace/add_product.html', {'form': form})

@login_required
def add_farm(request):
    if request.method == 'POST':
        form = FarmForm(request.POST)
        if form.is_valid():
            farm = form.save(commit=False)
            farm.farmer = request.user
            farm.save()
            messages.success(request, 'Farm added successfully!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = FarmForm()
    return render(request, 'marketplace/add_farm.html', {'form': form})

# Place order
@login_required
def place_order(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'POST':
        try:
            quantity = float(request.POST.get('quantity'))
            delivery_address = request.POST.get('delivery_address')
            total_price = quantity * float(product.price_per_unit)
            
            order = Order.objects.create(
                buyer=request.user,
                farmer=product.farmer,
                product=product,
                quantity=quantity,
                total_price=total_price,
                delivery_address=delivery_address
            )
            
            # Create delivery record
            Delivery.objects.create(
                order=order,
                pickup_location=product.farm.location,
                dropoff_location=delivery_address
            )
            
            messages.success(request, 'Order placed successfully!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error placing order: {str(e)}')
    
    return render(request, 'marketplace/place_order.html', {'product': product})

# Update delivery status (for transporters)
@login_required
def update_delivery(request, delivery_id):
    delivery = get_object_or_404(Delivery, id=delivery_id)
    
    # If transporter is accepting this delivery for the first time
    if delivery.transporter is None and request.user.profile.role == 'transporter':
        delivery.transporter = request.user
        delivery.save()
        messages.success(request, 'You have accepted this delivery!')
    
    if request.method == 'POST':
        form = DeliveryStatusForm(request.POST, instance=delivery)
        if form.is_valid():
            delivery = form.save(commit=False)
            if delivery.status == 'delivered':
                delivery.order.status = 'delivered'
                delivery.order.save()
                messages.success(request, 'Delivery marked as delivered!')
            delivery.save()
            messages.success(request, 'Delivery status updated!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = DeliveryStatusForm(instance=delivery)
    
    return render(request, 'marketplace/update_delivery.html', {'form': form, 'delivery': delivery})

# Admin: approve user
@login_required
def approve_user(request, user_id):
    if request.user.profile.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Permission denied. Only admins can approve users.')
        return redirect('dashboard')
    
    profile = get_object_or_404(Profile, user_id=user_id)
    profile.is_approved = True
    profile.save()
    messages.success(request, f'User {profile.user.username} has been approved!')
    return redirect('dashboard')

# Admin: official prices
@login_required
def official_prices(request):
    if request.user.profile.role != 'admin' and not request.user.is_superuser:
        messages.error(request, 'Permission denied. Only admins can access official prices.')
        return redirect('dashboard')
    
    products = Product.objects.values('category').distinct()
    return render(request, 'marketplace/official_prices.html', {'products': products})

# Product listing for buyers
@login_required
def product_list(request):
    products = Product.objects.filter(available=True)
    return render(request, 'marketplace/product_list.html', {'products': products})