from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add-product/', views.add_product, name='add_product'),
    path('add-farm/', views.add_farm, name='add_farm'),
    path('product-list/', views.product_list, name='product_list'),
    path('place-order/<int:product_id>/', views.place_order, name='place_order'),
    path('update-delivery/<int:delivery_id>/', views.update_delivery, name='update_delivery'),
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('official-prices/', views.official_prices, name='official_prices'),
]