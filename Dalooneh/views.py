from django.shortcuts import render, redirect
from django.db.models import Count, Sum
from menu.models import Category, Product
from orders.models import OrderItem
from tables.models import TableSession
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import json
import os

@ensure_csrf_cookie
def home_view(request):
    categories = Category.objects.filter(is_active=True)
    
    # Get popular products based on order history (most ordered products)
    popular_products = Product.objects.filter(
        is_active=True, 
        is_available=True
    ).annotate(
        total_ordered=Sum('orderitem__quantity')
    ).exclude(
        total_ordered__isnull=True
    ).order_by('-total_ordered')[:10]
    
    # Check if redirected from table_access (QR code scan)
    show_phone_modal = request.session.pop('show_phone_modal', False)
    print(f"DEBUG: show_phone_modal = {show_phone_modal}")
    
    context = {
        'categories': categories,
        'popular_products': popular_products,
        'show_phone_modal': show_phone_modal
    }
    
    return render(request, 'home.html', context)

def test_phone_modal(request):
    """Test view to directly set the show_phone_modal flag and redirect to home"""
    request.session['show_phone_modal'] = True
    print("DEBUG: Test view setting show_phone_modal = True")
    return redirect('home')

@never_cache
@csrf_protect
def management_login_view(request):
    """Login view specifically for management panel access"""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('staff:management_index')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        next_url = request.POST.get('next', '/staff/')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_superuser:
                    login(request, user)
                    messages.success(request, f'Welcome {user.get_full_name() or user.username}')
                    return redirect(next_url)
                else:
                    messages.error(request, 'You do not have access to the management panel. Only superusers can log in.')
            else:
                messages.error(request, 'Username or password is incorrect.')
        else:
            messages.error(request, 'Please enter username and password.')
    
    next_url = request.GET.get('next', '/staff/')
    context = {
        'next': next_url
    }
    return render(request, 'management/login.html', context)

def management_logout_view(request):
    """Logout view for management panel"""
    if request.user.is_authenticated:
        messages.success(request, 'You have successfully logged out.')
        logout(request)
    return redirect('menu:menu')

def custom_logout_view(request):
    """Custom logout view that accepts both GET and POST requests"""
    if request.user.is_authenticated:
        messages.success(request, 'You have successfully logged out.')
        logout(request)
    return redirect('home')  # Redirect to root URL

@login_required
def management_dashboard(request):
    """Main management dashboard - redirects to staff management index"""
    if not request.user.is_superuser:
        messages.error(request, 'You do not have access to this section.')
        return redirect('home')
    
    # Redirect to the existing staff management index
    return redirect('staff:management_index')

@require_http_methods(["GET"])
def manifest_view(request):
    """Serve the PWA manifest.json file"""
    manifest_data = {
        "name": "Dalooneh - Restaurant Menu",
        "short_name": "Dalooneh",
        "description": "Dalooneh Restaurant Online Ordering System",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#033F38",
        "orientation": "portrait-primary",
        "scope": "/",
        "lang": "en",
        "dir": "ltr",
        "icons": [
            {
                "src": "/static/images/icons/icon-72x72.png",
                "sizes": "72x72",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-96x96.png",
                "sizes": "96x96",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-128x128.png",
                "sizes": "128x128",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-144x144.png",
                "sizes": "144x144",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-152x152.png",
                "sizes": "152x152",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-384x384.png",
                "sizes": "384x384",
                "type": "image/png",
                "purpose": "maskable any"
            },
            {
                "src": "/static/images/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable any"
            }
        ],
        "categories": ["food", "restaurant", "business"],
        "shortcuts": [
            {
                "name": "Food Menu",
                "short_name": "Menu",
                "description": "View restaurant menu",
                "url": "/menu/",
                "icons": [
                    {
                        "src": "/static/images/icons/icon-96x96.png",
                        "sizes": "96x96"
                    }
                ]
            },
            {
                "name": "Shopping Cart",
                "short_name": "Cart",
                "description": "View shopping cart",
                "url": "/cart/",
                "icons": [
                    {
                        "src": "/static/images/icons/icon-96x96.png",
                        "sizes": "96x96"
                    }
                ]
            }
        ],
        "prefer_related_applications": False
    }
    
    response = JsonResponse(manifest_data)
    response['Content-Type'] = 'application/manifest+json'
    return response 