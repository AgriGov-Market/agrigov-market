from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Admin
    path('management/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('management/users/', views.admin_user_list, name='admin_user_list'),
    path('official-prices/', views.official_prices, name='official_prices'),

    # Farmer
    path('farmer/dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('farmer/add-farm/', views.add_farm, name='add_farm'),
    path('farmer/add-product/', views.add_product, name='add_product'),
    path('farmer/edit-product/<int:product_id>/', views.edit_product, name='edit_product'),
    path('farmer/delete-product/<int:product_id>/', views.delete_product, name='delete_product'),

    # Buyer
    path('buyer/dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('products/', views.product_list, name='product_list'),
    path('place-order/<int:product_id>/', views.place_order, name='place_order'),

    # Transporter
    path('transporter/dashboard/', views.transporter_dashboard, name='transporter_dashboard'),
    path('update-delivery/<int:delivery_id>/', views.update_delivery, name='update_delivery'),
]
