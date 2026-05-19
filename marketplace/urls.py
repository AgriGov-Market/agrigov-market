from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.auth_view, name='register'),
    path('login/', views.auth_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('users/<int:user_id>/', views.public_profile, name='public_profile'),
    path('rate/<int:order_id>/<int:user_id>/', views.rate_user, name='rate_user'),

    # Admin
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/users/', views.admin_user_list, name='admin_user_list'),
    path('management/users/<int:user_id>/', views.admin_user_detail, name='admin_user_detail'),
    path('management/users/<int:user_id>/delete/', views.admin_delete_user, name='admin_delete_user'),
    path('management/orders/', views.admin_order_list, name='admin_order_list'),
    path('management/orders/<int:order_id>/', views.admin_order_detail, name='admin_order_detail'),
    path('management/products/<int:product_id>/delete/', views.admin_delete_product, name='admin_delete_product'),
    path('management/products/bulk-delete/', views.admin_bulk_delete_products, name='admin_bulk_delete_products'),
    path('official-prices/', views.official_prices, name='official_prices'),
    path('official-prices/<int:price_id>/edit/', views.edit_official_price, name='edit_official_price'),
    path('official-prices/<int:price_id>/delete/', views.delete_official_price, name='delete_official_price'),
    path('categories/', views.categories, name='categories'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # Farmer
    path('farmer/dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('farmer/add-farm/', views.add_farm, name='add_farm'),
    path('farmer/edit-farm/<int:farm_id>/', views.edit_farm, name='edit_farm'),
    path('farmer/delete-farm/<int:farm_id>/', views.delete_farm, name='delete_farm'),
    path('farmer/add-product/', views.add_product, name='add_product'),
    path('farmer/edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('farmer/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),
    path('farmer/accept-order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('farmer/reject-order/<int:order_id>/', views.reject_order, name='reject_order'),
    path('farm/<int:farm_id>/', views.farm_detail, name='farm_detail'),

    # Buyer
    path('buyer/dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('place-order/<int:product_id>/', views.place_order, name='place_order'),
    path('products/dashboard/', views.products_dashboard, name='products_dashboard'),
    path('products/visual-search/', views.ai_image_search, name='ai_image_search'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/dismiss/', views.dismiss_notification, name='dismiss_notification'),
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

    # Transporter
    path('transporter/dashboard/', views.transporter_dashboard, name='transporter_dashboard'),
    path('transporter/accept-delivery/<int:order_id>/', views.accept_delivery, name='accept_delivery'),
    path('transporter/reject-delivery/<int:order_id>/', views.reject_delivery, name='reject_delivery'),
    path('update-delivery/<int:delivery_id>/', views.update_delivery, name='update_delivery'),
]
