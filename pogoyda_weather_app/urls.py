from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index_url'),
    path('register/', views.custom_register, name='custom_register'),
    path('email_notify/', views.email_notify, name='email_notify'),
    path('login/', views.custom_login, name='custom_login'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('password_reset/', views.custom_password_reset, name='password_reset'),
    path('recovery_account/<token>/', views.custom_recovery_account, name='custom_recovery_account'),
    path('create_fav/', views.create_favorites, name='create_favorites'),
    path('show_favorites/', views.show_favorites, name='show_favorites'),
    path('confirm/<token>/', views.custom_confirm, name='custom_confirm'),
    path('incorrect_city/<city>', views.incorrect_city, name='incorrect_city'),
    path('API_error/', views.redirect_to_api_error, name='redirect_to_api_error'),
]