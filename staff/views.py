from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDate, TruncHour
from datetime import datetime, timedelta
from .models import StaffUser, Report, StaffLog
from orders.models import Order, OrderItem, Payment
from menu.models import Product, Category
from customers.models import Customer, CustomerRating
from Dalooneh.decorators import superuser_required

def is_staff(user):
    return hasattr(user, 'staff')

@superuser_required
@login_required
def management_index(request):
    """Main management index page with links to all management sections"""
    return render(request, 'staff/management_index.html')

@login_required
@user_passes_test(is_staff)
def dashboard(request):
    # Get today's statistics
    today = timezone.now().date()
    today_orders = Order.objects.filter(created_at__date=today)
    today_revenue = sum(order.final_amount for order in today_orders)
    
    # Get pending orders
    pending_orders = Order.objects.filter(status='pending').order_by('created_at')
    
    # Get recent orders
    recent_orders = Order.objects.all().order_by('-created_at')[:5]
    
    # Get staff activity
    staff_activity = StaffLog.objects.filter(
        created_at__date=today
    ).order_by('-created_at')[:10]
    
    # Get customer statistics
    customer_stats = {
        'total': Customer.objects.count(),
        'active': Customer.objects.filter(is_active=True).count(),
        'new_today': Customer.objects.filter(created_at__date=today).count()
    }
    
    context = {
        'today_orders_count': today_orders.count(),
        'today_revenue': today_revenue,
        'pending_orders': pending_orders,
        'recent_orders': recent_orders,
        'staff_activity': staff_activity,
        'customer_stats': customer_stats
    }
    
    return render(request, 'staff/dashboard.html', context)

@login_required
@user_passes_test(is_staff)
def order_list(request):
    # Get filter parameters
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    orders = Order.objects.all()
    
    # Apply filters
    if status:
        orders = orders.filter(status=status)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    orders = orders.order_by('-created_at')
    
    # Log view
    StaffLog.objects.create(
        staff=request.user.staff,
        action='order_list_view',
        details=f'Viewed order list with filters: status={status}, date_from={date_from}, date_to={date_to}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return render(request, 'staff/order_list.html', {
        'orders': orders,
        'filters': {
            'status': status,
            'date_from': date_from,
            'date_to': date_to
        }
    })

@login_required
@user_passes_test(is_staff)
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            old_status = order.status
            order.status = new_status
            order.save()
            
            # Log status change
            StaffLog.objects.create(
                staff=request.user.staff,
                action='order_status_change',
                details=f'Order {order.order_number} status changed from {old_status} to {new_status}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            messages.success(request, 'Order status updated successfully.')
            return redirect('staff:order_detail', order_id=order.id)
    
    # Get order history
    order_history = StaffLog.objects.filter(
        action__in=['order_status_change', 'payment_create'],
        details__contains=order.order_number
    ).order_by('-created_at')
    
    return render(request, 'staff/order_detail.html', {
        'order': order,
        'order_history': order_history
    })

@superuser_required
@login_required
@user_passes_test(is_staff)
def product_management(request):
    products = Product.objects.all().order_by('category', 'name')
    categories = Category.objects.all()
    
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        is_available = request.POST.get('is_available') == 'true'
        
        product = get_object_or_404(Product, id=product_id)
        product.is_available = is_available
        product.save()
        
        # Log product update
        StaffLog.objects.create(
            staff=request.user.staff,
            action='product_update',
            details=f'Product {product.name} availability changed to {is_available}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return redirect('staff:product_management')
    
    return render(request, 'staff/product_management.html', {
        'products': products,
        'categories': categories
    })

@superuser_required
@login_required
@user_passes_test(is_staff)
def category_management(request):
    categories = Category.objects.all().order_by('name')
    
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        is_active = request.POST.get('is_active') == 'true'
        
        category = get_object_or_404(Category, id=category_id)
        category.is_active = is_active
        category.save()
        
        # Log category update
        StaffLog.objects.create(
            staff=request.user.staff,
            action='category_update',
            details=f'Category {category.name} active status changed to {is_active}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return redirect('staff:category_management')
    
    return render(request, 'staff/category_management.html', {'categories': categories})

@login_required
@user_passes_test(is_staff)
def reports(request):
    if request.method == 'POST':
        report_type = request.POST.get('report_type')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        # Convert dates
        start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get orders in date range
        orders = Order.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        # Calculate statistics
        total_orders = orders.count()
        total_revenue = sum(order.final_amount for order in orders)
        total_discounts = sum(order.discount_amount for order in orders)
        
        # Get hourly distribution
        hourly_distribution = orders.annotate(
            hour=TruncHour('created_at')
        ).values('hour').annotate(
            count=Count('id'),
            revenue=Sum('final_amount')
        ).order_by('hour')
        
        # Get product statistics
        product_stats = OrderItem.objects.filter(
            order__in=orders
        ).values('product__name').annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('price')
        ).order_by('-total_quantity')
        
        # Get customer statistics
        customer_stats = orders.values('customer__user__username').annotate(
            total_orders=Count('id'),
            total_spent=Sum('final_amount')
        ).order_by('-total_spent')
        
        # Create report
        report = Report.objects.create(
            type=report_type,
            start_date=start_date,
            end_date=end_date,
            total_orders=total_orders,
            total_revenue=total_revenue,
            total_discounts=total_discounts,
            created_by=request.user.staff
        )
        
        # Log report creation
        StaffLog.objects.create(
            staff=request.user.staff,
            action='report_generate',
            details=f'Generated {report_type} report for {start_date} to {end_date}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        messages.success(request, 'Report created successfully.')
        return redirect('staff:reports')
    
    # Get recent reports
    recent_reports = Report.objects.all().order_by('-created_at')[:5]
    
    return render(request, 'staff/reports.html', {'recent_reports': recent_reports})

@login_required
@user_passes_test(is_staff)
def staff_activity(request):
    # Get filter parameters
    staff_id = request.GET.get('staff')
    action = request.GET.get('action')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Base queryset
    activities = StaffLog.objects.all()
    
    # Apply filters
    if staff_id:
        activities = activities.filter(staff_id=staff_id)
    if action:
        activities = activities.filter(action=action)
    if date_from:
        activities = activities.filter(created_at__date__gte=date_from)
    if date_to:
        activities = activities.filter(created_at__date__lte=date_to)
    
    activities = activities.order_by('-created_at')
    
    # Get staff list for filter
    staff_list = StaffUser.objects.all()
    
    return render(request, 'staff/activity.html', {
        'activities': activities,
        'staff_list': staff_list,
        'filters': {
            'staff_id': staff_id,
            'action': action,
            'date_from': date_from,
            'date_to': date_to
        }
    })
