from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import UserProfile, TransporterInfo, Farm, Product, Order, Delivery, OfficialPrice, ProductCategory
from .forms import RegisterForm, FarmForm, ProductForm, OrderForm, DeliveryForm, OfficialPriceForm, ProductCategoryForm

# Helper functions
def get_user_type(user):
    try:
        return user.userprofile.user_type
    except:
        return None

def is_admin(user):
    return user.is_superuser or get_user_type(user) == 'admin'

def is_farmer(user):
    return get_user_type(user) == 'farmer'

def is_buyer(user):
    return get_user_type(user) == 'buyer'

def is_transporter(user):
    return get_user_type(user) == 'transporter'

# Registration (fixes NOT NULL constraint)
def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()

            user_type = form.cleaned_data['user_type']
            UserProfile.objects.create(
                user=user,
                user_type=user_type,
                phone=form.cleaned_data.get('phone', ''),
                address=form.cleaned_data.get('address', '')
            )

            if user_type == 'transporter':
                TransporterInfo.objects.create(
                    user=user,
                    capacity_kg=form.cleaned_data['capacity_kg'],
                    vehicle_number=form.cleaned_data.get('vehicle_number', '')
                )

            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'marketplace/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    return render(request, 'marketplace/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def home(request):
    return render(request, 'marketplace/home.html')

@login_required
def dashboard(request):
    user_type = get_user_type(request.user)
    if user_type == 'admin' or request.user.is_superuser:
        return redirect('admin_dashboard')
    elif user_type == 'farmer':
        return redirect('farmer_dashboard')
    elif user_type == 'buyer':
        return redirect('buyer_dashboard')
    elif user_type == 'transporter':
        return redirect('transporter_dashboard')
    else:
        return redirect('home')

# Admin views
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_products = Product.objects.count()
    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_products': total_products,
    }
    return render(request, 'marketplace/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    all_users = User.objects.select_related('userprofile', 'transporterinfo').all()
    return render(request, 'marketplace/admin_user_list.html', {'all_users': all_users})

def official_prices(request):
    prices = OfficialPrice.objects.all().order_by('-effective_date')
    categories = ProductCategory.objects.all()
    if request.method == 'POST':
        if not request.user.is_authenticated or not is_admin(request.user):
            messages.error(request, 'Only administrators can add official prices.')
            return redirect('official_prices')
        action = request.POST.get('action')
        if action == 'add_category':
            category_form = ProductCategoryForm(request.POST, prefix='category')
            form = OfficialPriceForm(prefix='price')
            if category_form.is_valid():
                category_form.save()
                messages.success(request, 'Product category added successfully.')
                return redirect('official_prices')
        else:
            form = OfficialPriceForm(request.POST, prefix='price')
            category_form = ProductCategoryForm(prefix='category')
            if form.is_valid():
                form.save()
                messages.success(request, 'Official price added successfully.')
                return redirect('official_prices')
    else:
        form = OfficialPriceForm(prefix='price')
        category_form = ProductCategoryForm(prefix='category')
    context = {
        'prices': prices,
        'categories': categories,
        'form': form,
        'category_form': category_form,
    }
    return render(request, 'marketplace/official_prices.html', context)

# Farmer views
@login_required
@user_passes_test(is_farmer)
def farmer_dashboard(request):
    farms = Farm.objects.filter(farmer=request.user)
    products = Product.objects.filter(farmer=request.user).select_related('category').annotate(order_count=Count('order'))
    orders = Order.objects.filter(product__farmer=request.user).select_related('product', 'buyer')
    context = {
        'farms': farms,
        'products': products,
        'orders': orders,
    }
    return render(request, 'marketplace/farmer_dashboard.html', context)

@login_required
@user_passes_test(is_farmer)
def add_farm(request):
    if request.method == 'POST':
        form = FarmForm(request.POST)
        if form.is_valid():
            farm = form.save(commit=False)
            farm.farmer = request.user
            farm.save()
            messages.success(request, 'Farm added successfully.')
            return redirect('farmer_dashboard')
    else:
        form = FarmForm()
    return render(request, 'marketplace/add_farm.html', {'form': form})

@login_required
@user_passes_test(is_farmer)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.name = product.category.name
            product.save()
            messages.success(request, 'Product added successfully.')
            return redirect('farmer_dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/add_product.html', {'form': form})


@login_required
@user_passes_test(is_farmer)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.name = product.category.name
            product.save()
            messages.success(request, 'Product updated successfully.')
            return redirect('farmer_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'marketplace/edit_product.html', {'form': form, 'product': product})


@login_required
@user_passes_test(is_farmer)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    if request.method != 'POST':
        return redirect('farmer_dashboard')

    if Order.objects.filter(product=product).exists():
        messages.error(request, 'This product cannot be deleted because it already has orders.')
        return redirect('farmer_dashboard')

    if product.image:
        product.image.delete(save=False)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('farmer_dashboard')

# Buyer views
@login_required
@user_passes_test(is_buyer)
def buyer_dashboard(request):
    products = Product.objects.filter(available=True)
    orders = Order.objects.filter(buyer=request.user).select_related('product')
    context = {
        'products': products,
        'orders': orders,
    }
    return render(request, 'marketplace/buyer_dashboard.html', context)

def product_list(request):
    products = Product.objects.filter(available=True).select_related('category', 'farmer')
    return render(request, 'marketplace/product_list.html', {'products': products})

@login_required
@user_passes_test(is_buyer)
def place_order(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    if request.method == 'POST':
        form = OrderForm(request.POST, product=product)
        if form.is_valid():
            order = form.save(commit=False)
            order.product = product
            order.buyer = request.user
            order.total_price = order.quantity * product.price_per_unit
            order.save()
            Delivery.objects.create(order=order)
            # Reduce product quantity
            product.quantity -= order.quantity
            if product.quantity == 0:
                product.available = False
            product.save()
            messages.success(request, 'Order placed successfully.')
            return redirect('buyer_dashboard')
    else:
        form = OrderForm(product=product)
    return render(request, 'marketplace/place_order.html', {'form': form, 'product': product})

# Transporter views
@login_required
@user_passes_test(is_transporter)
def transporter_dashboard(request):
    deliveries = Delivery.objects.filter(
        Q(transporter=request.user) | Q(transporter__isnull=True)
    ).select_related('order__product', 'order__buyer')
    transporter_info = TransporterInfo.objects.filter(user=request.user).first()
    context = {
        'deliveries': deliveries,
        'transporter_info': transporter_info,
    }
    return render(request, 'marketplace/transporter_dashboard.html', context)

@login_required
@user_passes_test(is_transporter)
def update_delivery(request, delivery_id):
    delivery = get_object_or_404(
        Delivery.objects.select_related('order__product', 'order__buyer'),
        Q(id=delivery_id),
        Q(transporter=request.user) | Q(transporter__isnull=True),
    )
    if request.method == 'POST':
        form = DeliveryForm(request.POST, instance=delivery)
        if form.is_valid():
            delivery = form.save(commit=False)
            if delivery.transporter is None:
                delivery.transporter = request.user
            delivery.save()
            messages.success(request, 'Delivery updated successfully.')
            return redirect('transporter_dashboard')
    else:
        form = DeliveryForm(instance=delivery)
    return render(request, 'marketplace/update_delivery.html', {'form': form, 'delivery': delivery})
