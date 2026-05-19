from decimal import Decimal
import json
import os
import urllib.parse
from django.conf import settings
from django.db.models import Avg, Count, Q, F
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.urls import reverse
from PIL import Image
import numpy as np

TORCH_AVAILABLE = False
try:
    import torch
    import torchvision.models as models
    import torchvision.transforms as T
    from sklearn.metrics.pairwise import cosine_similarity
    TORCH_AVAILABLE = True
except Exception:
    TORCH_AVAILABLE = False

from .models import UserProfile, TransporterInfo, Farm, Product, ProductImage, Order, Delivery, OfficialPrice, ProductCategory, Rating, WishlistItem
from .forms import RegisterForm, FarmForm, ProductForm, OrderForm, DeliveryForm, DeliveryFeeForm, OfficialPriceForm, ProductCategoryForm, UserAccountForm, UserProfileForm, TransporterInfoForm, RatingForm
from .notifications import get_user_notifications, is_valid_notification_id
from .models import DismissedNotification, UserNotification

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


def save_product_images(product, uploaded_images):
    if not uploaded_images:
        return
    for uploaded_image in uploaded_images:
        if uploaded_image:
            ProductImage.objects.create(product=product, image=uploaded_image)


def get_category_hierarchy_json():
    parents = ProductCategory.objects.filter(parent__isnull=True, is_active=True).order_by('name').prefetch_related('subcategories')
    result = []
    for parent in parents:
        children = []
        for child in parent.subcategories.filter(is_active=True).order_by('name'):
            children.append({
                'id': child.id,
                'name': child.name,
                'min_price': str(child.min_price) if child.min_price is not None else None,
                'max_price': str(child.max_price) if child.max_price is not None else None,
            })
        result.append({
            'id': parent.id,
            'name': parent.name,
            'min_price': str(parent.min_price) if parent.min_price is not None else None,
            'max_price': str(parent.max_price) if parent.max_price is not None else None,
            'children': children,
        })
    return json.dumps(result)


def ensure_delivery_records():
    orders_without_delivery = Order.objects.filter(delivery__isnull=True)
    for order in orders_without_delivery:
        Delivery.objects.get_or_create(order=order)


_IMAGE_MODEL = None
_IMAGE_TRANSFORM = None

def get_image_model_and_transform():
    global _IMAGE_MODEL, _IMAGE_TRANSFORM
    if _IMAGE_MODEL is not None and _IMAGE_TRANSFORM is not None:
        return _IMAGE_MODEL, _IMAGE_TRANSFORM

    if not TORCH_AVAILABLE:
        raise RuntimeError('AI image search is not available because the required packages are missing.')

    try:
        weights = models.ResNet50_Weights.DEFAULT
        base_model = models.resnet50(weights=weights)
    except Exception:
        base_model = models.resnet50(pretrained=True)

    feature_model = torch.nn.Sequential(*list(base_model.children())[:-1])
    feature_model.eval()
    _IMAGE_MODEL = feature_model
    _IMAGE_TRANSFORM = T.Compose([
        T.Resize(256),
        T.CenterCrop(224),
        T.ToTensor(),
        T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    return _IMAGE_MODEL, _IMAGE_TRANSFORM


def get_image_features(image_source):
    image = Image.open(image_source)
    image = image.convert('RGB')
    model, transform = get_image_model_and_transform()
    tensor = transform(image).unsqueeze(0)
    with torch.no_grad():
        features = model(tensor)
    features = features.squeeze().cpu().numpy()
    return features.reshape(-1)


def get_product_image_path(product):
    if product.image and getattr(product.image, 'path', None):
        return product.image.path
    first_image = product.images.first()
    if first_image and first_image.image and getattr(first_image.image, 'path', None):
        return first_image.image.path
    return None


def find_similar_products_from_image(uploaded_file, top_n=20):
    if not TORCH_AVAILABLE:
        raise RuntimeError('AI image search is not available because the required packages are missing.')

    query_features = get_image_features(uploaded_file)
    products = Product.objects.filter(available=True).select_related('category', 'farmer', 'farm').prefetch_related('images')
    scored = []
    for product in products:
        image_path = get_product_image_path(product)
        if not image_path or not os.path.exists(image_path):
            continue
        try:
            product_features = get_image_features(image_path)
        except Exception:
            continue
        score = float(cosine_similarity([query_features], [product_features])[0][0])
        scored.append((score, product))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [product for _, product in scored[:top_n]]


def build_products_dashboard_context(request, products, q, sort, active_category, ai_message=None):
    page_obj = Paginator(products, 10).get_page(request.GET.get('page'))
    product_cards = [product_card_payload(product, request.user) for product in page_obj.object_list]

    available_qs = Product.objects.filter(
        available=True,
    ).select_related('category', 'farmer')

    # If showing AI search results, use only matched products for stats
    stats_qs = products if ai_message else available_qs

    def get_group_count(group_name):
        qs = stats_qs if ai_message else available_qs
        if ai_message:
            # For AI results, filter the matched products by category
            product_ids = {p.id for p in qs}
            return Product.objects.filter(
                Q(category__name=group_name) | Q(category__parent__name=group_name),
                id__in=product_ids
            ).count()
        return qs.filter(
            Q(category__name=group_name) | Q(category__parent__name=group_name)
        ).count()

    crops_count = get_group_count('Crops & Produce')
    livestock_count = get_group_count('Livestock')
    animal_products_count = get_group_count('Animal Products')
    total_products = len(products) if ai_message else available_qs.count()

    stats = {
        'total_products': total_products,
        'crops': crops_count,
        'livestock': livestock_count,
        'animal_products': animal_products_count,
    }

    inventory = {
        'total': total_products,
        'breakdown': [
            {'label': 'Crops & Produce', 'count': crops_count, 'percent': int((crops_count / total_products) * 100) if total_products else 0, 'color': '#2ecc71'},
            {'label': 'Livestock', 'count': livestock_count, 'percent': int((livestock_count / total_products) * 100) if total_products else 0, 'color': '#f39c12'},
            {'label': 'Animal Products', 'count': animal_products_count, 'percent': int((animal_products_count / total_products) * 100) if total_products else 0, 'color': '#e74c3c'},
        ]
    }

    real_top_qs = available_qs.order_by('-quantity')[:5] if not ai_message else []
    top_sellers = [product_card_payload(p, request.user) for p in real_top_qs]
    recent_products = available_qs.order_by('-created_at')[:5] if not ai_message else []
    recent_activity = []
    for p in recent_products:
        recent_activity.append({
            'message': f'New product "{p.display_name or p.name}" added',
            'time': p.created_at.strftime('%b %d, %Y'),
            'icon_class': 'fa-box',
        })

    return {
        'products': product_cards,
        'stats': stats,
        'top_sellers': top_sellers,
        'recent_activity': recent_activity,
        'inventory': inventory,
        'active_category': active_category,
        'active_category_label': active_category,
        'q': q,
        'sort': sort,
        'page_obj': page_obj,
        'ai_message': ai_message,
    }


def ai_image_search(request):
    if request.method == 'POST':
        query_image = request.FILES.get('query_image')
        if not query_image:
            messages.error(request, 'Upload an image to start AI search.')
            return redirect('products_dashboard')

        if not TORCH_AVAILABLE:
            messages.error(request, 'AI image search is not available. PyTorch packages are not properly installed.')
            return redirect('products_dashboard')

        try:
            products = find_similar_products_from_image(query_image, top_n=50)
            if products:
                ai_message = 'AI is here — visual search returned these matching products.'
            else:
                ai_message = 'AI search completed but found no visually similar products.'
        except RuntimeError as e:
            messages.error(request, f'AI error: {str(e)}')
            return redirect('products_dashboard')
        except Exception as e:
            messages.error(request, f'Unable to process image: {str(e)}')
            return redirect('products_dashboard')

        request.session['ai_image_search_ids'] = [p.id for p in products]
        request.session['ai_image_search_message'] = ai_message
        request.session.modified = True
        return redirect(f"{reverse('ai_image_search')}?ai=1")

    if request.GET.get('ai') != '1':
        return redirect('products_dashboard')

    image_ids = request.session.get('ai_image_search_ids', [])
    ai_message = request.session.get('ai_image_search_message', 'AI is here — visual search results.')
    products = []
    if image_ids:
        product_map = {p.id: p for p in Product.objects.filter(id__in=image_ids).select_related('category', 'farmer', 'farm').prefetch_related('images')}
        products = [product_map[i] for i in image_ids if i in product_map]

    context = build_products_dashboard_context(request, products, q='', sort='newest', active_category='', ai_message=ai_message)
    return render(request, 'marketplace/products_dashboard.html', context)



def valid_ratings_received(user):
    orders_without_delivery = Order.objects.filter(delivery__isnull=True)
    for order in orders_without_delivery:
        Delivery.objects.get_or_create(order=order)

def sync_order_status_from_delivery(delivery):
    if delivery.delivery_status == 'delivered':
        delivery.order.status = 'delivered'
    elif delivery.delivery_status in ['assigned', 'picked_up', 'in_transit']:
        delivery.order.status = 'shipped'
    elif delivery.delivery_status == 'cancelled':
        delivery.order.status = 'cancelled'
    elif delivery.delivery_status == 'rejected':
        delivery.order.status = 'confirmed'
    else:
        delivery.order.status = 'confirmed'
    delivery.order.save(update_fields=['status'])

def valid_ratings_received(user):
    return Rating.objects.filter(
        rated_user=user,
        order__status='delivered',
    ).filter(
        Q(rater=F('order__buyer')) |
        Q(rater=F('order__product__farmer')) |
        Q(rater=F('order__delivery__transporter'))
    )

def average_rating_for(user):
    rating = valid_ratings_received(user).aggregate(avg=Avg('score'), count=Count('id'))
    return {
        'avg': round(rating['avg'], 1) if rating['avg'] else None,
        'count': rating['count'],
    }

def participant_users_for_order(order):
    """Return the users who participated in an order: buyer, product.farmer and transporter (if any).

    This helper is used by rating-related logic to determine valid raters and
    ratees for an order.
    """
    participants = []
    # buyer
    try:
        if order.buyer:
            participants.append(order.buyer)
    except Exception:
        pass

    # product farmer
    try:
        if getattr(order, 'product', None) and getattr(order.product, 'farmer', None):
            participants.append(order.product.farmer)
    except Exception:
        pass

    # transporter (if delivery exists)
    try:
        transporter = getattr(getattr(order, 'delivery', None), 'transporter', None)
        if transporter:
            participants.append(transporter)
    except Exception:
        pass

    # return unique, non-null users
    seen = set()
    unique = []
    for u in participants:
        if u and u.id not in seen:
            unique.append(u)
            seen.add(u.id)
    return unique

def user_can_rate_order_target(user, order, rated_user):
    if order.status != 'delivered':
        return False
    if user == rated_user:
        return False
    participants = participant_users_for_order(order)
    if user not in participants or rated_user not in participants:
        return False
    transporter = getattr(getattr(order, 'delivery', None), 'transporter', None)
    if rated_user == transporter:
        return get_user_type(user) in ['buyer', 'farmer']
    return True


def rating_lookup_for(user, orders):
    ratings = Rating.objects.filter(rater=user, order__in=orders).select_related('rated_user')
    return {f"{rating.order_id}:{rating.rated_user_id}": rating for rating in ratings}

def ratings_by_user_id(users):
    return {user.id: average_rating_for(user) for user in users if user}

def auth_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    register_form = RegisterForm()
    login_username = ''
    if request.method == 'POST':
        action = request.POST.get('action', 'login')
        if action == 'login':
            login_username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            user = authenticate(request, username=login_username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            messages.error(request, 'Invalid username or password')
        else:
            register_form = RegisterForm(request.POST)
            if register_form.is_valid():
                user = register_form.save(commit=False)
                user.set_password(register_form.cleaned_data['password1'])
                user.is_active = True
                user.save()

                user_type = register_form.cleaned_data['user_type']
                UserProfile.objects.create(
                    user=user,
                    user_type=user_type,
                    is_validated=True,
                    validation_rejection_reason='',
                    phone=register_form.cleaned_data.get('phone', ''),
                    address=register_form.cleaned_data.get('address', '')
                )

                if user_type == 'transporter':
                    TransporterInfo.objects.create(
                        user=user,
                        capacity_kg=register_form.cleaned_data['capacity_kg'],
                        vehicle_number=register_form.cleaned_data.get('vehicle_number', '')
                    )

                login(request, user)
                messages.success(request, 'Registration successful! You are now logged in.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Please correct the errors below.')

    return render(request, 'marketplace/login_register.html', {
        'form': register_form,
        'login_username': login_username,
    })

def logout_view(request):
    logout(request)
    return redirect('home')


def home(request):
    farmers_count = User.objects.filter(userprofile__user_type='farmer').count()
    orders_count = Order.objects.count()
    transporters_count = User.objects.filter(userprofile__user_type='transporter').count()
    ratings_avg = Rating.objects.aggregate(avg=Avg('score'))['avg']
    products_count = Product.objects.filter(available=True).count()
    prices_count = OfficialPrice.objects.count()

    featured_products = Product.objects.filter(available=True).select_related('farm', 'category').prefetch_related('images').order_by('-created_at')[:6]
    featured_product_cards = []
    for product in featured_products:
        try:
            image_url = product.first_image_url
        except Exception:
            image_url = None

        farm = getattr(product, 'farm', None)
        location = 'Algeria'
        if farm:
            location = farm.wilaya or farm.city or farm.location or 'Algeria'

        featured_product_cards.append({
            'id': product.id,
            'name': product.display_name,
            'category': product.category.name if product.category else 'Marketplace product',
            'price': product.price_per_unit,
            'unit': product.unit,
            'location': location,
            'image_url': image_url,
        })

    latest_prices = []
    seen_prices = set()
    for price in OfficialPrice.objects.order_by('commodity', '-effective_date', '-id'):
        commodity_key = price.commodity.lower()
        if commodity_key in seen_prices:
            continue
        seen_prices.add(commodity_key)
        latest_prices.append(price)
        if len(latest_prices) == 5:
            break

    latest_price_rows = [
        {
            'commodity': price.commodity,
            'unit': 'kg',
            'price': price.price_per_kg,
            'effective_date': price.effective_date,
        }
        for price in latest_prices
    ]

    testimonials = list(
        Rating.objects.select_related('rater', 'rater__userprofile')
        .exclude(comment='')
        .order_by('-updated_at')[:3]
    )
    testimonial_cards = []
    for testimonial in testimonials:
        full_name = testimonial.rater.get_full_name().strip() if testimonial.rater else ''
        testimonial_cards.append({
            'comment': testimonial.comment,
            'name': full_name or testimonial.rater.username,
            'role': getattr(getattr(testimonial.rater, 'userprofile', None), 'get_user_type_display', lambda: 'User')(),
            'initial': (full_name or testimonial.rater.username or 'U')[:1].upper(),
        })

    if len(testimonial_cards) < 3:
        testimonial_cards = [
            {
                'comment': 'Listing products is simple and buyers reach out faster than before.',
                'name': 'Ahmed B.',
                'role': 'Farmer',
                'initial': 'A',
            },
            {
                'comment': 'I can compare fresh produce and official prices in one place.',
                'name': 'Fatima K.',
                'role': 'Buyer',
                'initial': 'F',
            },
            {
                'comment': 'Delivery coordination feels much clearer with shared order tracking.',
                'name': 'Yacine M.',
                'role': 'Transporter',
                'initial': 'Y',
            },
        ]

    context = {
        'farmers_count': farmers_count,
        'orders_count': orders_count,
        'transporters_count': transporters_count,
        'products_count': products_count,
        'prices_count': prices_count,
        'trust_score': round(ratings_avg or 5, 1),
        'featured_products': featured_product_cards,
        'latest_prices': latest_price_rows,
        'latest_price_update': latest_price_rows[0]['effective_date'] if latest_price_rows else None,
        'testimonials': testimonial_cards,
        'public_landing': True,
    }
    return render(request, 'marketplace/home.html', context)

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

@login_required
def notifications(request):
    notifications = get_user_notifications(request)
    return render(request, 'marketplace/notifications.html', {
        'notifications': notifications,
    })


@login_required
@csrf_exempt
def dismiss_notification(request):
    # Accept JSON or form POST with 'id'
    if request.method != 'POST':
        return HttpResponseBadRequest('Invalid method')

    try:
        if request.content_type == 'application/json':
            payload = json.loads(request.body.decode('utf-8') or '{}')
            notif_id = str(payload.get('id', '') or '')
        else:
            notif_id = str(request.POST.get('id', '') or '')
    except Exception:
        notif_id = ''

    if not notif_id:
        return HttpResponseBadRequest('Missing id')

    if not is_valid_notification_id(notif_id, user=request.user):
        return HttpResponseBadRequest('Invalid notification id')

    if request.user.is_authenticated:
        DismissedNotification.objects.get_or_create(user=request.user, notification_id=notif_id)
    else:
        dismissed = request.session.get('dismissed_notifications', []) or []
        if notif_id not in dismissed:
            dismissed.append(notif_id)
            request.session['dismissed_notifications'] = dismissed
            request.session.modified = True

    return JsonResponse({'success': True, 'id': notif_id})

@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={'user_type': 'admin' if request.user.is_superuser else 'buyer'},
    )
    transporter_info = None
    if profile_obj.user_type == 'transporter':
        transporter_info, _ = TransporterInfo.objects.get_or_create(
            user=request.user,
            defaults={'capacity_kg': 0, 'vehicle_number': ''},
        )

    if request.method == 'POST':
        account_form = UserAccountForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, instance=profile_obj)
        transporter_form = TransporterInfoForm(request.POST, instance=transporter_info) if transporter_info else None
        forms_valid = account_form.is_valid() and profile_form.is_valid()
        if transporter_form:
            forms_valid = forms_valid and transporter_form.is_valid()
        if forms_valid:
            account_form.save()
            profile_form.save()
            if transporter_form:
                transporter_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        account_form = UserAccountForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile_obj)
        transporter_form = TransporterInfoForm(instance=transporter_info) if transporter_info else None

    return render(request, 'marketplace/profile.html', {
        'account_form': account_form,
        'profile_form': profile_form,
        'transporter_form': transporter_form,
        'profile_obj': profile_obj,
        'rating_summary': average_rating_for(request.user),
    })

@login_required
def public_profile(request, user_id):
    viewed_user = get_object_or_404(User.objects.select_related('userprofile'), id=user_id)
    products = Product.objects.filter(farmer=viewed_user, available=True).select_related('category', 'farm')
    completed_orders = Order.objects.filter(
        Q(buyer=viewed_user) |
        Q(product__farmer=viewed_user) |
        Q(delivery__transporter=viewed_user),
        status='delivered',
    ).select_related('product__farmer', 'buyer', 'delivery__transporter').distinct()[:10]
    reviews = valid_ratings_received(viewed_user).select_related('rater', 'order').order_by('-updated_at')
    return render(request, 'marketplace/public_profile.html', {
        'viewed_user': viewed_user,
        'viewed_profile': getattr(viewed_user, 'userprofile', None),
        'rating_summary': average_rating_for(viewed_user),
        'products': products,
        'completed_orders': completed_orders,
        'reviews': reviews,
    })

# Admin views
@login_required
@user_passes_test(is_admin)
@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    total_orders = Order.objects.count()
    total_products = Product.objects.count()
    active_farmers = User.objects.filter(userprofile__user_type='farmer', is_active=True).count()
    farmer_count = User.objects.filter(userprofile__user_type='farmer').count()
    buyer_count = User.objects.filter(userprofile__user_type='buyer').count()
    transporter_count = User.objects.filter(userprofile__user_type='transporter').count()
    price_records = OfficialPrice.objects.count()

    # Get products with search
    search_query = request.GET.get('search', '')
    products = Product.objects.select_related('farmer', 'category').prefetch_related('images', 'order_set')
    if search_query:
        products = products.filter(name__icontains=search_query) | products.filter(farmer__username__icontains=search_query)

    def percent(count):
        return round((count / total_users) * 100) if total_users else 0

    context = {
        'total_users': total_users,
        'total_orders': total_orders,
        'total_products': total_products,
        'active_farmers': active_farmers,
        'products': products,
        'my_rating': average_rating_for(request.user),
        'price_records': price_records,
        'user_distribution': [
            {'label': 'Farmers', 'count': farmer_count, 'percent': percent(farmer_count)},
            {'label': 'Buyers', 'count': buyer_count, 'percent': percent(buyer_count)},
            {'label': 'Transporters', 'count': transporter_count, 'percent': percent(transporter_count)},
        ],
        'search_query': search_query,
    }
    return render(request, 'marketplace/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def admin_user_list(request):
    query = (request.GET.get('q') or '').strip()
    all_users = User.objects.select_related('userprofile', 'transporterinfo').all()
    if query:
        all_users = all_users.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )
    return render(request, 'marketplace/admin_user_list.html', {'all_users': all_users, 'q': query})


@login_required
@user_passes_test(is_admin)
def admin_user_detail(request, user_id):
    viewed_user = get_object_or_404(User.objects.select_related('userprofile', 'transporterinfo'), id=user_id)
    viewed_profile = getattr(viewed_user, 'userprofile', None)
    transporter_info = getattr(viewed_user, 'transporterinfo', None)
    products = Product.objects.filter(farmer=viewed_user, available=True).select_related('category', 'farm')
    completed_orders = Order.objects.filter(
        Q(buyer=viewed_user) |
        Q(product__farmer=viewed_user) |
        Q(delivery__transporter=viewed_user),
        status='delivered',
    ).select_related('product__farmer', 'buyer', 'delivery__transporter').distinct()[:10]
    reviews = valid_ratings_received(viewed_user).select_related('rater', 'order').order_by('-updated_at')
    return render(request, 'marketplace/admin_user_detail.html', {
        'viewed_user': viewed_user,
        'viewed_profile': viewed_profile,
        'transporter_info': transporter_info,
        'rating_summary': average_rating_for(viewed_user),
        'products': products,
        'completed_orders': completed_orders,
        'reviews': reviews,
    })


@login_required
@user_passes_test(is_admin)
def admin_delete_user(request, user_id):
    if request.method != 'POST':
        return redirect('admin_user_list')
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, 'You cannot delete your own admin account.')
        return redirect('admin_user_list')
    username = user.username
    user.delete()
    messages.success(request, f'User "{username}" deleted successfully.')
    return redirect('admin_user_list')


@login_required
@user_passes_test(is_admin)
def approve_user(request, user_id):
    if request.method != 'POST':
        return redirect('admin_user_list')
    user = get_object_or_404(User.objects.select_related('userprofile'), id=user_id)
    profile = getattr(user, 'userprofile', None)
    if profile:
        profile.is_validated = True
        profile.validation_rejection_reason = ''
        profile.save(update_fields=['is_validated', 'validation_rejection_reason'])
    user.is_active = True
    user.save(update_fields=['is_active'])
    messages.success(request, f'User {user.username} approved and activated.')
    return redirect('admin_user_list')


@login_required
@user_passes_test(is_admin)
def reject_user(request, user_id):
    user = get_object_or_404(User.objects.select_related('userprofile'), id=user_id)
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        profile = getattr(user, 'userprofile', None)
        if profile:
            profile.is_validated = False
            profile.validation_rejection_reason = reason
            profile.save(update_fields=['is_validated', 'validation_rejection_reason'])
        user.is_active = False
        user.save(update_fields=['is_active'])
        messages.success(request, f'User {user.username} has been rejected.')
    return redirect('admin_user_list')


@login_required
@user_passes_test(is_admin)
def admin_delete_product(request, product_id):
    """Allow admin to delete any product"""
    product = get_object_or_404(Product, id=product_id)
    if request.method != 'POST':
        return redirect('admin_dashboard')
    
    product_name = product.display_name
    
    # Delete product images
    for image_obj in product.images.all():
        if image_obj.image:
            image_obj.image.delete(save=False)
    # Delete legacy image
    if product.image:
        product.image.delete(save=False)
    
    product.delete()
    messages.success(request, f'Product "{product_name}" has been deleted successfully.')
    return redirect('admin_dashboard')


@login_required
@user_passes_test(is_admin)
def admin_bulk_delete_products(request):
    """Allow admin to delete all products via bulk action"""
    if request.method == 'POST':
        products = Product.objects.all()
        deleted_count = 0
        
        for product in products:
            # Delete product images
            for image_obj in product.images.all():
                if image_obj.image:
                    image_obj.image.delete(save=False)
            # Delete legacy image
            if product.image:
                product.image.delete(save=False)
            deleted_count += 1
        
        # Delete all products
        total = products.count()
        products.delete()
        messages.success(request, f'Successfully deleted all {total} products from the marketplace.')
    
    return redirect('admin_dashboard')

@login_required
@user_passes_test(is_admin)
def admin_order_list(request):
    ensure_delivery_records()
    orders = Order.objects.select_related(
        'product__farmer__userprofile',
        'buyer__userprofile',
        'delivery__transporter__userprofile',
    ).order_by('-order_date')
    return render(request, 'marketplace/admin_order_list.html', {'orders': orders})

@login_required
@user_passes_test(is_admin)
def admin_order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('product__farmer', 'buyer', 'delivery__transporter'),
        id=order_id,
    )
    delivery, _ = Delivery.objects.get_or_create(order=order)
    if request.method == 'POST':
        form = DeliveryFeeForm(request.POST, instance=delivery)
        if form.is_valid():
            form.save()
            messages.success(request, 'Delivery fee updated successfully.')
            return redirect('admin_order_detail', order_id=order.id)
    else:
        form = DeliveryFeeForm(instance=delivery)
    return render(request, 'marketplace/admin_order_detail.html', {'order': order, 'delivery': delivery, 'form': form})

def official_prices(request):
    categories = ProductCategory.objects.filter(parent__isnull=True).prefetch_related('subcategories')
    prices = OfficialPrice.objects.all().order_by('-effective_date')
    selected_parent = None
    selected_parent_id = request.GET.get('parent_category')
    if selected_parent_id:
        try:
            selected_parent = categories.get(id=selected_parent_id)
            subcategory_names = [sub.name for sub in selected_parent.subcategories.filter(is_active=True)]
            if subcategory_names:
                prices = prices.filter(commodity__in=subcategory_names)
            else:
                prices = prices.none()
        except ProductCategory.DoesNotExist:
            selected_parent = None

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
        'selected_parent': selected_parent,
        'form': form,
        'category_form': category_form,
    }
    return render(request, 'marketplace/official_prices.html', context)


def categories(request):
    categories = ProductCategory.objects.filter(parent__isnull=True).prefetch_related('subcategories')
    if request.method == 'POST':
        if not request.user.is_authenticated or not is_admin(request.user):
            messages.error(request, 'Only administrators can manage categories.')
            return redirect('categories')
        category_form = ProductCategoryForm(request.POST, prefix='category')
        if category_form.is_valid():
            category_form.save()
            messages.success(request, 'Category added successfully.')
            return redirect('categories')
    else:
        category_form = ProductCategoryForm(prefix='category')

    return render(request, 'marketplace/categories.html', {
        'categories': categories,
        'category_form': category_form,
    })


def get_category_product_count(category):
    category_ids = [category.id]
    queue = [category]
    while queue:
        parent = queue.pop()
        children = list(parent.subcategories.all())
        for child in children:
            category_ids.append(child.id)
            queue.append(child)
    return Product.objects.filter(category_id__in=category_ids).count()


@login_required
@user_passes_test(is_admin)
def edit_category(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, instance=category, prefix='category')
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated successfully.')
            return redirect('categories')
    else:
        form = ProductCategoryForm(instance=category, prefix='category')
    return render(request, 'marketplace/edit_category.html', {
        'category': category,
        'category_form': form,
    })


@login_required
@user_passes_test(is_admin)
def delete_category(request, category_id):
    category = get_object_or_404(ProductCategory, id=category_id)
    if request.method != 'POST':
        return redirect('categories')
    total_products = get_category_product_count(category)
    if total_products > 0:
        messages.error(request, f'Unable to delete "{category.name}" because {total_products} product(s) are still assigned to it or its subcategories.')
        return redirect('categories')
    category.delete()
    messages.success(request, f'Category "{category.name}" deleted successfully.')
    return redirect('categories')


@login_required
@user_passes_test(is_admin)
def edit_official_price(request, price_id):
    price = get_object_or_404(OfficialPrice, id=price_id)
    if request.method == 'POST':
        form = OfficialPriceForm(request.POST, instance=price, prefix='price')
        if form.is_valid():
            form.save()
            messages.success(request, 'Official price updated successfully.')
            return redirect('official_prices')
    else:
        form = OfficialPriceForm(instance=price, prefix='price')
    return render(request, 'marketplace/edit_official_price.html', {
        'official_price': price,
        'form': form,
    })


@login_required
@user_passes_test(is_admin)
def delete_official_price(request, price_id):
    price = get_object_or_404(OfficialPrice, id=price_id)
    if request.method != 'POST':
        return redirect('official_prices')
    price.delete()
    messages.success(request, f'Official price record for "{price.commodity}" deleted successfully.')
    return redirect('official_prices')


# Farmer views
@login_required
@user_passes_test(is_farmer)
def farmer_dashboard(request):
    ensure_delivery_records()
    farms = Farm.objects.filter(farmer=request.user)
    products = Product.objects.filter(farmer=request.user).select_related('category').annotate(order_count=Count('order'))
    orders = Order.objects.filter(product__farmer=request.user).select_related('product', 'buyer', 'buyer__userprofile', 'delivery__transporter__userprofile')
    orders_list = list(orders)
    confirmed_orders_count = sum(1 for o in orders_list if o.status in ['confirmed', 'delivered'])
    related_users = []
    for order in orders_list:
        related_users.extend([order.buyer, getattr(order.delivery, 'transporter', None) if hasattr(order, 'delivery') else None])
    context = {
        'farms': farms,
        'products': products,
        'orders': orders_list,
        'confirmed_orders_count': confirmed_orders_count,
        'my_rating': average_rating_for(request.user),
        'rating_lookup': rating_lookup_for(request.user, orders_list),
        'ratings_by_user': ratings_by_user_id(related_users),
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
def edit_farm(request, farm_id):
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)
    if request.method == 'POST':
        form = FarmForm(request.POST, instance=farm)
        if form.is_valid():
            form.save()
            messages.success(request, 'Farm updated successfully.')
            return redirect('farmer_dashboard')
    else:
        form = FarmForm(instance=farm)
    return render(request, 'marketplace/edit_farm.html', {'form': form, 'farm': farm})

@login_required
@user_passes_test(is_farmer)
def delete_farm(request, farm_id):
    farm = get_object_or_404(Farm, id=farm_id, farmer=request.user)
    if request.method != 'POST':
        return redirect('farmer_dashboard')
    
    # Check if farm has products linked to it through the farmer
    # Note: Products are linked to farmer, not directly to farm
    # So we just delete the farm
    farm.delete()
    messages.success(request, 'Farm deleted successfully.')
    return redirect('farmer_dashboard')

@login_required
@user_passes_test(is_farmer)
def add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, farmer=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()
            uploaded_images = request.FILES.getlist('images')
            save_product_images(product, uploaded_images)
            messages.success(request, 'Product added successfully.')
            return redirect('farmer_dashboard')
    else:
        form = ProductForm(farmer=request.user)
    latest_prices = OfficialPrice.objects.order_by('commodity', '-effective_date', '-id')
    suggested_ranges = {}
    seen = set()
    for official_price in latest_prices:
        if official_price.commodity.lower() in seen:
            continue
        seen.add(official_price.commodity.lower())
        min_price = official_price.price_per_kg * Decimal('0.80')
        max_price = official_price.price_per_kg * Decimal('1.20')
        suggested_ranges[official_price.commodity.lower()] = {
            'commodity': official_price.commodity,
            'price': official_price.price_per_kg,
            'min': min_price,
            'max': max_price,
        }
    categories_json = get_category_hierarchy_json()
    return render(request, 'marketplace/add_product.html', {
        'form': form,
        'suggested_ranges': suggested_ranges,
        'categories_json': categories_json,
    })


@login_required
@user_passes_test(is_farmer)
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, farmer=request.user)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()
            uploaded_images = request.FILES.getlist('images')
            save_product_images(product, uploaded_images)
            messages.success(request, 'Product updated successfully.')
            return redirect('farmer_dashboard')
    else:
        form = ProductForm(instance=product, farmer=request.user)
    categories_json = get_category_hierarchy_json()
    return render(request, 'marketplace/edit_product.html', {
        'form': form,
        'product': product,
        'categories_json': categories_json,
    })


@login_required
@user_passes_test(is_farmer)
def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id, farmer=request.user)
    if request.method != 'POST':
        return redirect('farmer_dashboard')

    if Order.objects.filter(product=product).exists():
        messages.error(request, 'This product cannot be deleted because it already has orders.')
        return redirect('farmer_dashboard')

    for image_obj in product.images.all():
        if image_obj.image:
            image_obj.image.delete(save=False)
    if product.image:
        product.image.delete(save=False)
    product.delete()
    messages.success(request, 'Product deleted successfully.')
    return redirect('farmer_dashboard')

# Buyer views
@login_required
@user_passes_test(is_buyer)
def buyer_dashboard(request):
    ensure_delivery_records()
    products = Product.objects.filter(available=True)
    orders = Order.objects.filter(buyer=request.user).select_related('product__farmer__userprofile', 'delivery__transporter__userprofile')
    orders_list = list(orders)
    delivered_orders_count = sum(1 for o in orders_list if o.status == 'delivered')
    active_orders_count = sum(1 for o in orders_list if o.status in ['pending', 'confirmed'])
    related_users = []
    for order in orders_list:
        related_users.extend([order.product.farmer, getattr(order.delivery, 'transporter', None) if hasattr(order, 'delivery') else None])
    context = {
        'products': products,
        'orders': orders_list,
        'delivered_orders_count': delivered_orders_count,
        'active_orders_count': active_orders_count,
        'my_rating': average_rating_for(request.user),
        'rating_lookup': rating_lookup_for(request.user, orders_list),
        'ratings_by_user': ratings_by_user_id(related_users),
    }
    return render(request, 'marketplace/buyer_dashboard.html', context)

def product_list(request):
    # Redirect to the new products dashboard to show the enhanced UI
    from django.shortcuts import redirect
    return redirect('products_dashboard')


def product_card_payload(prod, request_user=None):
    def make_svg_data_uri(text, bg='#e8f5e9', fg='#2b5c15', w=480, h=320):
        svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='{w}' height='{h}' viewBox='0 0 {w} {h}' preserveAspectRatio='xMidYMid meet'>
  <rect width='100%' height='100%' fill='{bg}' />
  <text x='50%' y='50%' font-family='Segoe UI, Tahoma, sans-serif' font-size='28' fill='{fg}' dominant-baseline='middle' text-anchor='middle'>{text}</text>
</svg>"""
        return 'data:image/svg+xml;utf8,' + urllib.parse.quote(svg)

    if prod.first_image_url:
        image_url = prod.first_image_url
    else:
        image_url = make_svg_data_uri(prod.name)

    category_name = prod.category.name if prod.category else ''
    category_key = category_name.lower()
    if 'veget' in category_key:
        category_group = 'vegetables'
        category_badge_class = 'badge-vegetables'
    elif 'fruit' in category_key:
        category_group = 'fruits'
        category_badge_class = 'badge-fruits'
    elif 'meat' in category_key:
        category_group = 'meat'
        category_badge_class = 'badge-meat'
    else:
        category_group = 'other'
        category_badge_class = 'badge-other'

    user_type = get_user_type(request_user) if request_user and request_user.is_authenticated else None
    is_owner = bool(request_user and request_user.is_authenticated and prod.farmer_id == request_user.id)

    farm = getattr(prod, 'farm', None)
    return {
        'id': prod.id,
        'name': prod.display_name or prod.name,
        'price': prod.price_per_unit,
        'stock': prod.quantity or 0,
        'unit': prod.unit or 'kg',
        'image_url': image_url,
        'category': category_name or 'Other',
        'category_group': category_group,
        'category_badge_class': category_badge_class,
        'farmer': prod.farmer.username,
        'farmer_id': prod.farmer.id,
        'farm': farm.name if farm else 'No farm selected',
        'farm_id': farm.id if farm else None,
        'is_owner': is_owner,
        'can_order': user_type == 'buyer' and not is_owner and prod.available,
        'show_wishlist': user_type == 'buyer' and not is_owner,
    }


def products_dashboard(request):
    """Render the product dashboard in a screenshot-style layout using database data."""
    q = (request.GET.get('q') or '').strip()
    raw_category = (request.GET.get('category') or '').strip()
    sort = (request.GET.get('sort') or 'newest').strip()

    group_filters = {
        'crops': 'Crops & Produce',
        'livestock': 'Livestock',
        'animal_products': 'Animal Products',
        'seeds_plants': 'Seeds & Plants',
        'supplies': 'Farming Supplies',
        'equipment': 'Equipment & Tools',
        'animal_care': 'Animal Care',
        'services': 'Farm Services',
    }

    base_qs = Product.objects.filter(
        available=True,
    ).select_related('category', 'farmer', 'farm').prefetch_related('images')
    if q:
        base_qs = base_qs.filter(
            Q(name__icontains=q) |
            Q(description__icontains=q) |
            Q(category__name__icontains=q) |
            Q(farm__name__icontains=q) |
            Q(farmer__username__icontains=q) |
            Q(farmer__first_name__icontains=q) |
            Q(farmer__last_name__icontains=q)
        )

    if sort == 'price_low':
        base_qs = base_qs.order_by('price_per_unit', '-created_at')
    elif sort == 'price_high':
        base_qs = base_qs.order_by('-price_per_unit', '-created_at')
    else:
        sort = 'newest'
        base_qs = base_qs.order_by('-created_at')

    active_category = raw_category if raw_category in group_filters else ''
    active_category_label = group_filters.get(active_category, '')

    available_qs = Product.objects.filter(
        available=True,
    ).select_related('category', 'farmer')

    def get_group_count(group_name):
        return available_qs.filter(
            Q(category__name=group_name) | Q(category__parent__name=group_name)
        ).count()

    crops_count = get_group_count('Crops & Produce')
    livestock_count = get_group_count('Livestock')
    animal_products_count = get_group_count('Animal Products')
    total_products = available_qs.count()

    if active_category:
        group_name = group_filters[active_category]
        filtered_qs = base_qs.filter(
            Q(category__name=group_name) | Q(category__parent__name=group_name)
        )
    else:
        filtered_qs = base_qs

    paginator = Paginator(filtered_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    product_cards = [product_card_payload(product, request.user) for product in page_obj.object_list]

    stats = {
        'total_products': total_products,
        'crops': crops_count,
        'livestock': livestock_count,
        'animal_products': animal_products_count,
    }

    # Inventory breakdown for the right-side widget (percentages)
    def percent(part, whole):
        return int((part / whole) * 100) if whole else 0

    inventory = {
        'total': total_products,
        'breakdown': [
            {'label': 'Crops & Produce', 'count': crops_count, 'percent': percent(crops_count, total_products), 'color': '#2ecc71'},
            {'label': 'Livestock', 'count': livestock_count, 'percent': percent(livestock_count, total_products), 'color': '#f39c12'},
            {'label': 'Animal Products', 'count': animal_products_count, 'percent': percent(animal_products_count, total_products), 'color': '#e74c3c'},
        ]
    }

    real_top_qs = available_qs.order_by('-quantity')[:5]
    top_sellers = [product_card_payload(p, request.user) for p in real_top_qs]

    recent_products = available_qs.order_by('-created_at')[:5]
    recent_activity = []
    for p in recent_products:
        recent_activity.append({
            'message': f'New product "{p.display_name or p.name}" added',
            'time': p.created_at.strftime('%b %d, %Y'),
            'icon_class': 'fa-box',
        })

    return render(request, 'marketplace/products_dashboard.html', {
        'products': product_cards,
        'stats': stats,
        'top_sellers': top_sellers,
        'recent_activity': recent_activity,
        'inventory': inventory,
        'active_category': active_category,
        'active_category_label': active_category_label,
        'q': q,
        'sort': sort,
        'page_obj': page_obj,
    })

def product_detail(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category', 'farmer', 'farm'), id=product_id)
    return render(request, 'marketplace/product_detail.html', {'product': product})


def farm_detail(request, farm_id):
    farm = get_object_or_404(Farm.objects.select_related('farmer'), id=farm_id)
    products = farm.products.filter(available=True).select_related('category')[:12]
    rating = average_rating_for(farm.farmer)
    return render(request, 'marketplace/farm_detail.html', {
        'farm': farm,
        'products': products,
        'rating_summary': rating,
    })


@login_required
def wishlist(request):
    qs = WishlistItem.objects.filter(user=request.user).select_related('product__category', 'product__farmer')
    items = []
    available_to_order = 0
    for it in qs:
        p = it.product
        item = product_card_payload(p, request.user)
        item['added_at'] = it.created_at
        if item['can_order']:
            available_to_order += 1
        items.append(item)
    return render(request, 'marketplace/wishlist.html', {
        'items': items,
        'available_to_order_count': available_to_order,
    })


@login_required
def add_to_wishlist(request, product_id):
    if request.method != 'POST':
        return redirect('products_dashboard')
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.get_or_create(user=request.user, product=product)
    messages.success(request, f'Added "{product.display_name}" to your wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'products_dashboard'))


@login_required
def remove_from_wishlist(request, product_id):
    if request.method != 'POST':
        return redirect('wishlist')
    product = get_object_or_404(Product, id=product_id)
    WishlistItem.objects.filter(user=request.user, product=product).delete()
    messages.success(request, f'Removed "{product.display_name}" from your wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))


@login_required
def remove_from_wishlist(request, product_id):
    # kept as a single implementation above; this serves as a safe alias if called twice
    if request.method != 'POST':
        return redirect('wishlist')
    WishlistItem.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, 'Removed item from wishlist.')
    return redirect(request.META.get('HTTP_REFERER', 'wishlist'))

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
            order.status = 'pending'
            order.save()

            Delivery.objects.get_or_create(order=order)

            # create notification for the product farmer about the new order
            try:
                farmer = product.farmer
                if farmer and farmer != request.user:
                    UserNotification.objects.create(
                        user=farmer,
                        title=f'New order #{order.id}',
                        message=f'{request.user.username} placed an order for {product.display_name} (qty: {order.quantity}).',
                        url=reverse('farmer_dashboard')
                    )
            except Exception:
                pass
            
            # Reduce product quantity
            product.quantity -= order.quantity
            if product.quantity == 0:
                product.available = False
            product.save()
            
            messages.success(request, 'Order placed successfully. Transporter will be assigned.')
            return redirect('buyer_dashboard')
    else:
        form = OrderForm(product=product)
    return render(request, 'marketplace/place_order.html', {'form': form, 'product': product})

# Farmer actions on orders
@login_required
@user_passes_test(is_farmer)
def accept_order(request, order_id):
    if request.method != 'POST':
        return redirect('farmer_dashboard')
    order = get_object_or_404(Order.objects.select_related('product__farmer'), id=order_id, product__farmer=request.user)
    if order.status not in ['pending']:
        messages.error(request, 'Order cannot be accepted in its current state.')
        return redirect('farmer_dashboard')
    order.status = 'confirmed'
    order.rejection_reason = ''
    order.save(update_fields=['status', 'rejection_reason'])

    # notify the buyer that their order was accepted
    try:
        buyer = order.buyer
        if buyer and buyer != request.user:
            UserNotification.objects.create(
                user=buyer,
                title=f'Order #{order.id} confirmed',
                message=f'Your order for {order.product.display_name} has been accepted by {request.user.username}.',
                url=reverse('buyer_dashboard')
            )
    except Exception:
        pass

    messages.success(request, f'Order #{order.id} accepted and transporter will be assigned.')
    return redirect('farmer_dashboard')


@login_required
@user_passes_test(is_farmer)
def reject_order(request, order_id):
    order = get_object_or_404(Order.objects.select_related('product__farmer'), id=order_id, product__farmer=request.user)
    if request.method != 'POST':
        return redirect('farmer_dashboard')
    reason = request.POST.get('reason', '')
    if order.status not in ['pending']:
        messages.error(request, 'Order cannot be rejected in its current state.')
        return redirect('farmer_dashboard')
    order.status = 'cancelled'
    order.rejection_reason = reason
    order.save(update_fields=['status', 'rejection_reason'])
    # restore product quantity
    product = order.product
    product.quantity = F('quantity') + order.quantity
    product.available = True
    product.save()
    
    messages.success(request, f'Order #{order.id} rejected.')
    return redirect('farmer_dashboard')
# Transporter views
@login_required
@user_passes_test(is_transporter)
def transporter_dashboard(request):
    ensure_delivery_records()
    delivery_query = (request.GET.get('delivery_id') or '').strip()
    pending_requests = Order.objects.filter(
        delivery__transporter__isnull=True,
        delivery__delivery_status='pending',
        status__in=['pending', 'confirmed', 'shipped'],
    ).select_related('product__farmer__userprofile', 'buyer__userprofile', 'delivery').order_by('-order_date')
    active_deliveries = Delivery.objects.filter(
        transporter=request.user,
    ).exclude(
        delivery_status__in=['delivered', 'cancelled']
    ).select_related('order__product__farmer__userprofile', 'order__buyer__userprofile').order_by('-order__order_date')
    if delivery_query:
        # only allow numeric order id searches
        if delivery_query.isdigit():
            active_deliveries = active_deliveries.filter(order__id=int(delivery_query))
        else:
            active_deliveries = active_deliveries.none()
    completed_deliveries = Delivery.objects.filter(
        transporter=request.user,
        delivery_status='delivered',
    ).select_related('order__product__farmer__userprofile', 'order__buyer__userprofile')
    delivered_orders = [delivery.order for delivery in completed_deliveries]
    related_users = []
    for delivery in completed_deliveries:
        related_users.extend([delivery.order.buyer, delivery.order.product.farmer])
    transporter_info = TransporterInfo.objects.filter(user=request.user).first()
    reviews = valid_ratings_received(request.user).select_related('rater', 'order').order_by('-updated_at')
    total_reviews = reviews.count()
    score_counts = {score: 0 for score in range(1, 6)}
    for item in reviews.values('score').annotate(count=Count('id')):
        score_counts[item['score']] = item['count']
    distribution = [
        {
            'score': score,
            'count': score_counts[score],
            'percent': int((score_counts[score] / total_reviews) * 100) if total_reviews else 0,
        }
        for score in range(5, 0, -1)
    ]
    context = {
        'pending_requests': pending_requests,
        'active_deliveries': active_deliveries,
        'completed_deliveries': completed_deliveries,
        'transporter_info': transporter_info,
        'earnings': {
            'today': completed_deliveries.count() * 300,
            'week': completed_deliveries.count() * 300,
            'month': completed_deliveries.count() * 300,
        },
        'rating': average_rating_for(request.user)['avg'],
        'total_reviews': total_reviews,
        'reviews': reviews,
        'rating_lookup': rating_lookup_for(request.user, delivered_orders),
        'ratings_by_user': ratings_by_user_id(related_users),
        'rating_distribution': distribution,
        'recent_activities': [
            {
                'type': 'complete' if delivery.delivery_status == 'delivered' else 'accept',
                'message': f"Order #{delivery.order.id} - {delivery.order.product.display_name}",
                'time': delivery.order.order_date.strftime('%b %d, %Y'),
            }
            for delivery in active_deliveries[:5]
        ],
        'delivery_query': delivery_query,
    }
    return render(request, 'marketplace/transporter_dashboard.html', context)

@login_required
def rate_user(request, order_id, user_id):
    if request.method != 'POST':
        return redirect('dashboard')
    order = get_object_or_404(
        Order.objects.select_related('product__farmer', 'buyer', 'delivery__transporter'),
        id=order_id,
    )
    rated_user = get_object_or_404(User, id=user_id)
    if not user_can_rate_order_target(request.user, order, rated_user):
        messages.error(request, 'You can rate this user after a completed delivery you both participated in.')
        return redirect('dashboard')

    rating, _ = Rating.objects.get_or_create(
        order=order,
        rater=request.user,
        rated_user=rated_user,
        defaults={'score': 5},
    )
    form = RatingForm(request.POST, instance=rating)
    if form.is_valid():
        form.save()
        messages.success(request, f'Rating saved for {rated_user.username}.')
        # notify the rated user they received a rating
        try:
            score = getattr(rating, 'score', None)
            UserNotification.objects.create(
                user=rated_user,
                title=f'You received a rating',
                message=f'{request.user.username} rated you {score} stars for order #{order.id}.',
                url=reverse('dashboard')
            )
        except Exception:
            pass
    else:
        messages.error(request, 'Please choose a valid rating between 1 and 5.')
    return redirect('dashboard')

@login_required
@user_passes_test(is_transporter)
def accept_delivery(request, order_id):
    if request.method != 'POST':
        return redirect('transporter_dashboard')
    order = get_object_or_404(Order.objects.select_related('delivery'), id=order_id, status__in=['pending', 'confirmed', 'shipped'])
    delivery, _ = Delivery.objects.get_or_create(order=order)
    if delivery.transporter and delivery.transporter != request.user:
        messages.error(request, 'This delivery has already been accepted by another transporter.')
        return redirect('transporter_dashboard')
    delivery.transporter = request.user
    delivery.delivery_status = 'assigned'
    delivery.save(update_fields=['transporter', 'delivery_status'])
    sync_order_status_from_delivery(delivery)
    # notify buyer and farmer that a transporter accepted the delivery
    try:
        buyer = order.buyer
        farmer = getattr(order.product, 'farmer', None)
        if buyer and buyer != request.user:
            UserNotification.objects.create(
                user=buyer,
                title=f'Delivery assigned for order #{order.id}',
                message=f'{request.user.username} accepted the delivery for your order.',
                url=reverse('buyer_dashboard')
            )
        if farmer and farmer != request.user:
            UserNotification.objects.create(
                user=farmer,
                title=f'Delivery assigned for order #{order.id}',
                message=f'{request.user.username} will transport the order for {order.product.display_name}.',
                url=reverse('farmer_dashboard')
            )
    except Exception:
        pass

    messages.success(request, f'Delivery mission for order #{order.id} accepted.')
    return redirect('transporter_dashboard')

@login_required
@user_passes_test(is_transporter)
def reject_delivery(request, order_id):
    if request.method != 'POST':
        return redirect('transporter_dashboard')
    order = get_object_or_404(Order.objects.select_related('delivery'), id=order_id)
    delivery, _ = Delivery.objects.get_or_create(order=order)
    if delivery.transporter and delivery.transporter != request.user:
        messages.error(request, 'This delivery is assigned to another transporter.')
        return redirect('transporter_dashboard')
    delivery.transporter = None
    delivery.delivery_status = 'rejected'
    delivery.save(update_fields=['transporter', 'delivery_status'])
    sync_order_status_from_delivery(delivery)
    # notify buyer and farmer that the transporter rejected the delivery
    try:
        buyer = order.buyer
        farmer = getattr(order.product, 'farmer', None)
        if buyer:
            UserNotification.objects.create(
                user=buyer,
                title=f'Delivery rejected for order #{order.id}',
                message=f'A transporter rejected the delivery for your order. We will try to reassign.',
                url=reverse('buyer_dashboard')
            )
        if farmer:
            UserNotification.objects.create(
                user=farmer,
                title=f'Delivery rejected for order #{order.id}',
                message=f'A transporter rejected the delivery for order {order.id}.',
                url=reverse('farmer_dashboard')
            )
    except Exception:
        pass

    messages.success(request, f'Delivery mission for order #{order.id} rejected.')
    return redirect('transporter_dashboard')

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
            original_status = delivery.delivery_status
            original_transporter = delivery.transporter
            delivery = form.save(commit=False)
            if delivery.transporter is None:
                delivery.transporter = request.user
            delivery.save()
            sync_order_status_from_delivery(delivery)
            if delivery.delivery_status != original_status or (original_transporter is None and delivery.transporter is not None):
                # transporter assignment
                try:
                    if original_transporter is None and delivery.transporter is not None:
                        buyer = delivery.order.buyer
                        farmer = getattr(delivery.order.product, 'farmer', None)
                        transporter = delivery.transporter
                        if buyer:
                            UserNotification.objects.create(
                                user=buyer,
                                title=f'Transporter assigned for order #{delivery.order.id}',
                                message=f'{transporter.username} has been assigned to deliver your order.',
                                url=reverse('buyer_dashboard')
                            )
                        if farmer:
                            UserNotification.objects.create(
                                user=farmer,
                                title=f'Transporter assigned for order #{delivery.order.id}',
                                message=f'{transporter.username} will transport order #{delivery.order.id}.',
                                url=reverse('farmer_dashboard')
                            )
                except Exception:
                    pass
                # delivery status change notifications
                try:
                    if delivery.delivery_status != original_status:
                        buyer = delivery.order.buyer
                        farmer = getattr(delivery.order.product, 'farmer', None)
                        status = delivery.delivery_status
                        human = status.replace('_', ' ').title()
                        if buyer:
                            UserNotification.objects.create(
                                user=buyer,
                                title=f'Delivery {human} for order #{delivery.order.id}',
                                message=f'Delivery status updated to {human}.',
                                url=reverse('buyer_dashboard')
                            )
                        if farmer:
                            UserNotification.objects.create(
                                user=farmer,
                                title=f'Delivery {human} for order #{delivery.order.id}',
                                message=f'Delivery status updated to {human}.',
                                url=reverse('farmer_dashboard')
                            )
                        # also notify transporter
                        if delivery.transporter:
                            UserNotification.objects.create(
                                user=delivery.transporter,
                                title=f'Your delivery status updated ({human})',
                                message=f'Delivery #{delivery.id} status changed to {human}.',
                                url=reverse('transporter_dashboard')
                            )
                except Exception:
                    pass
            messages.success(request, 'Delivery updated successfully.')
            return redirect('transporter_dashboard')
    else:
        form = DeliveryForm(instance=delivery)
    return render(request, 'marketplace/update_delivery.html', {'form': form, 'delivery': delivery})
