from django.urls import path
from . import views

urlpatterns = [
    # Home & Auth
    path('',                        views.home,                  name='home'),
    path('register/',               views.register_view,         name='register'),
    path('login/',                  views.login_view,            name='login'),
    path('logout/',                 views.logout_view,           name='logout'),
    # Dashboard & Profile
    path('dashboard/',              views.dashboard,             name='dashboard'),
    path('profile/',                views.profile_view,          name='profile'),
    # Blood Requests
    path('request/submit/',         views.submit_request,        name='submit_request'),
    path('request/my/',             views.my_requests,           name='my_requests'),
    path('request/track/',          views.track_request,         name='track_request'),
    path('request/manage/',         views.manage_requests,       name='manage_requests'),
    path('request/<int:pk>/status/',views.update_request_status, name='update_request_status'),
    # Inventory
    path('inventory/',              views.inventory_view,        name='inventory'),
    path('inventory/add/',          views.add_inventory,         name='add_inventory'),
    path('inventory/<int:pk>/edit/',views.update_inventory,      name='update_inventory'),
    # Donor
    path('notifications/',          views.donor_notifications,   name='donor_notifications'),
    path('notifications/<int:pk>/respond/', views.respond_notification, name='respond_notification'),
    path('donations/',              views.donation_history,      name='donation_history'),
    path('donations/add/',          views.add_donation,          name='add_donation'),
    # Search (public)
    path('search/',                 views.search_blood,          name='search_blood'),
    # Admin
    path('admin-panel/users/',             views.admin_users,       name='admin_users'),
    path('admin-panel/users/<int:pk>/toggle/', views.toggle_user,   name='toggle_user'),
    path('admin-panel/staff/create/',      views.create_staff,      name='create_staff'),
    path('admin-panel/hospitals/',         views.admin_hospitals,   name='admin_hospitals'),
    path('admin-panel/reports/',           views.reports_view,      name='reports'),
]
