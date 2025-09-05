"""
Order management views.

This module handles all order-related functionality including:
- Cart management
- Order processing
- Payment handling
- Order history
- Analytics and reporting

Note: All date handling uses standard Gregorian calendar.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import send_mail
from django.conf import settings
import json
import datetime
from datetime import datetime, timedelta

from .models import Order, OrderItem, Payment
from menu.models import Product, Category
from customers.models import Customer, Discount
from staff.models import StaffLog
from tables.models import Table
from Dalooneh.decorators import superuser_required
from django.contrib.auth.models import User
"""Views for orders app.

All user-facing messages and texts are in English.
Date handling uses standard Gregorian calendar.
"""

# Create your views here.

@login_required
def cart_view(request):
    # Get or create customer
    customer, created = Customer.objects.get_or_create(user=request.user)
    
    # Get active order or create new one
    order, created = Order.objects.get_or_create(
        customer=customer,
        status='pending',
        defaults={
            'total_amount': 0,
            'discount_amount': 0,
            'final_amount': 0
        }
    )
    
    # Get available discounts
    available_discounts = customer.discounts.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    )
    
    return render(request, 'orders/cart.html', {
        'order': order,
        'available_discounts': available_discounts
    })

@require_POST
@login_required
def add_to_cart(request):
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        table_id = request.session.get('table_id')
        
        if not table_id:
            return JsonResponse({
                'success': False,
                'message': 'Please connect to a table first.'
            }, status=400)
        
        product = get_object_or_404(Product, id=product_id, is_active=True, is_available=True)
        customer = get_object_or_404(Customer, user=request.user)
        table = get_object_or_404(Table, id=table_id)
        
        # Get or create order
        order, created = Order.objects.get_or_create(
            customer=customer,
            table=table,
            status='pending',
            defaults={
                'total_amount': 0,
                'discount_amount': 0,
                'final_amount': 0
            }
        )
        
        # Check for duplicate items first and remove them
        duplicate_items = OrderItem.objects.filter(
            order=order,
            product=product
        )
        
        if duplicate_items.count() > 1:
            # Keep only one and delete others
            item_to_keep = duplicate_items.first()
            duplicate_items.exclude(id=item_to_keep.id).delete()
            
            # Update the remaining item
            item_to_keep.quantity = quantity
            item_to_keep.save()
            order_item = item_to_keep
            created = False
        else:
            # Add or update order item
            order_item, created = OrderItem.objects.get_or_create(
                order=order,
                product=product,
                defaults={'quantity': quantity, 'price': product.price}
            )
            
            if not created:
                order_item.quantity = quantity  # Replace instead of adding
                order_item.save()
        
        # Update order totals
        order.update_totals()
        
        # Log cart update
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='cart_update',
                details=f'Product {product.name} added to cart',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return JsonResponse({
            'success': True,
            'message': 'Product added to cart',
            'cart_count': order.items.count(),
            'order_total': order.final_amount
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@require_POST
@login_required
def remove_from_cart(request, item_id):
    try:
        order_item = get_object_or_404(OrderItem, id=item_id, order__customer__user=request.user)
        order = order_item.order
        order_item.delete()
        
        # Update order totals
        order.update_totals()
        
        return JsonResponse({
            'success': True,
            'message': 'Product removed from cart',
            'order_total': order.final_amount
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@require_POST
@login_required
def update_cart(request, item_id):
    try:
        quantity = int(request.POST.get('quantity', 1))
        order_item = get_object_or_404(OrderItem, id=item_id, order__customer__user=request.user)
        order = order_item.order
        
        if quantity > 0:
            order_item.quantity = quantity
            order_item.save()
        else:
            order_item.delete()
        
        # Update order totals
        order.update_totals()
        
        return JsonResponse({
            'success': True,
            'message': 'Cart updated',
            'order_total': order.final_amount
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@require_POST
@login_required
def apply_discount(request):
    try:
        discount_code = request.POST.get('discount_code')
        order_id = request.POST.get('order_id')
        
        order = get_object_or_404(Order, id=order_id, customer__user=request.user)
        discount = get_object_or_404(Discount, code=discount_code, customer=order.customer)
        
        if not discount.is_valid():
            return JsonResponse({
                'success': False,
                'message': 'Invalid or expired discount code.'
            }, status=400)
        
        # Apply discount
        order.discount_amount = (order.total_amount * discount.percentage) / 100
        order.final_amount = order.total_amount - order.discount_amount
        order.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Discount applied successfully',
            'discount_amount': order.discount_amount,
            'final_amount': order.final_amount
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

@login_required
def checkout(request):
    customer = get_object_or_404(Customer, user=request.user)
    order = get_object_or_404(Order, customer=customer, status='pending')
    
    if request.method == 'POST':
        # Get payment method and amount
        payment_method = request.POST.get('payment_method')
        amount = float(request.POST.get('amount', order.final_amount))
        
        # Create payment
        payment = Payment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method
        )
        
        # Update order status
        if payment.amount >= order.final_amount:
            order.status = 'confirmed'
            order.payment_status = 'paid'
        else:
            order.payment_status = 'partial'
        order.save()
        
        # Log payment
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='payment_create',
                details=f'Payment of {amount} created for order {order.order_number}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        messages.success(request, 'Payment completed successfully.')
        return redirect('orders:order_detail', order_id=order.id)
    
    return render(request, 'orders/checkout.html', {
        'order': order,
        'payment_methods': dict(Payment.PAYMENT_METHODS)
    })

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, customer__user=request.user)
    
    # Get payment history
    payments = order.payments.all().order_by('-created_at')
    
    return render(request, 'orders/order_detail.html', {
        'order': order,
        'payments': payments
    })

# Management Panel Views
def is_staff_or_superuser(user):
    return user.is_staff or user.is_superuser

@superuser_required
@login_required
def management_dashboard(request):
    # Get statistics for dashboard
    today = timezone.now().date()
    
    # Order statistics
    total_orders = Order.objects.count()
    today_orders = Order.objects.filter(created_at__date=today).count()
    
    # Payment statistics
    total_payments = Payment.objects.filter(status='completed').aggregate(Sum('amount'))['amount__sum'] or 0
    today_payments = Payment.objects.filter(status='completed', created_at__date=today).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Status statistics
    orders_by_status = Order.objects.values('status').annotate(count=Count('id'))
    orders_by_payment_status = Order.objects.values('payment_status').annotate(count=Count('id'))
    
    # Recent orders
    recent_orders = Order.objects.order_by('-created_at')[:10]
    
    context = {
        'total_orders': total_orders,
        'today_orders': today_orders,
        'total_payments': total_payments,
        'today_payments': today_payments,
        'orders_by_status': orders_by_status,
        'orders_by_payment_status': orders_by_payment_status,
        'recent_orders': recent_orders,
    }
    
    return render(request, 'orders/management/dashboard.html', context)

@superuser_required
@login_required
def management_order_list(request):
    # Filter parameters
    status = request.GET.get('status', '')
    payment_status = request.GET.get('payment_status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    customer_id = request.GET.get('customer_id', '')
    search_query = request.GET.get('q', '')
    
    # Start with all orders
    orders = Order.objects.all().order_by('-created_at')
    
    # Apply filters
    if status:
        orders = orders.filter(status=status)
    if payment_status:
        orders = orders.filter(payment_status=payment_status)
        
    # Handle date conversion for filtering
    if date_from:
        # Prefer ISO/Gregorian format
        try:
            orders = orders.filter(created_at__date__gte=date_from)
        except Exception:
            pass # No date conversion needed
    
    if date_to:
        try:
            orders = orders.filter(created_at__date__lte=date_to)
        except Exception:
            pass # No date conversion needed
    
    if customer_id:
        orders = orders.filter(customer_id=customer_id)
    
    # Apply customer search
    if search_query:
        # Search in customer information
        orders = orders.filter(
            Q(customer__user__first_name__icontains=search_query) |
            Q(customer__user__last_name__icontains=search_query) |
            Q(customer__phone_number__icontains=search_query) |
            Q(customer__id__icontains=search_query) |
            Q(order_number__icontains=search_query)
        )
    
    context = {
        'orders': orders,
        'status_choices': Order.STATUS_CHOICES,
        'payment_status_choices': Order.PAYMENT_STATUS_CHOICES,
        'selected_status': status,
        'selected_payment_status': payment_status,
        'date_from': date_from,
        'date_to': date_to,
        'search_query': search_query,
    }
    
    return render(request, 'orders/management/order_list.html', context)

@superuser_required
@login_required
def management_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    order_items = order.items.all()
    payments = order.payments.all().order_by('-created_at')
    
    context = {
        'order': order,
        'order_items': order_items,
        'payments': payments,
        'status_choices': Order.STATUS_CHOICES,
    }
    
    return render(request, 'orders/management/order_detail.html', context)

@superuser_required
@login_required
def management_order_edit(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        # Update order notes
        notes = request.POST.get('notes', '')
        order.notes = notes
        order.save()
        
        # Log order edit
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='order_edit',
                details=f'Order {order.order_number} edited',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        messages.success(request, 'Order updated successfully.')
        return redirect('orders:management_order_detail', order_id=order.id)
    
    context = {
        'order': order,
    }
    
    return render(request, 'orders/management/order_edit.html', context)

@superuser_required
@login_required
@require_POST
def management_order_update_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    new_status = request.POST.get('status')
    if new_status in dict(Order.STATUS_CHOICES):
        old_status = order.status
        order.status = new_status
        order.save()
        
        # Log status change
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='order_status_update',
                details=f'Order {order.order_number} status changed from {old_status} to {new_status}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        messages.success(request, 'Order status updated successfully.')
    else:
        messages.error(request, 'Invalid status.')
    
    return redirect('orders:management_order_detail', order_id=order.id)

@superuser_required
@login_required
def management_payment_list(request):
    # Filter parameters
    payment_method = request.GET.get('payment_method', '')
    status = request.GET.get('status', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all payments
    payments = Payment.objects.all().order_by('-created_at')
    
    # Apply filters
    if payment_method:
        payments = payments.filter(payment_method=payment_method)
    if status:
        payments = payments.filter(status=status)
        
    # Handle date conversion for filtering
    if date_from:
        try:
            # Convert date format
            gregorian_from = datetime.strptime(date_from, '%Y/%m/%d').date()
            payments = payments.filter(created_at__date__gte=gregorian_from)
        except (ValueError, TypeError):
            # If conversion fails, try original format as fallback
            try:
                payments = payments.filter(created_at__date__gte=date_from)
            except:
                pass
    
    if date_to:
        try:
            # Convert date format
            gregorian_to = datetime.strptime(date_to, '%Y/%m/%d').date()
            payments = payments.filter(created_at__date__lte=gregorian_to)
        except (ValueError, TypeError):
            # If conversion fails, try original format as fallback
            try:
                payments = payments.filter(created_at__date__lte=date_to)
            except:
                pass
    
    context = {
        'payments': payments,
        'payment_method_choices': Payment.PAYMENT_METHODS,
        'status_choices': Payment.STATUS_CHOICES,
        'selected_payment_method': payment_method,
        'selected_status': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'orders/management/payment_list.html', context)

@superuser_required
@login_required
def management_payment_detail(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    context = {
        'payment': payment,
    }
    
    return render(request, 'orders/management/payment_detail.html', context)

@superuser_required
@login_required
def management_payment_add(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        amount = request.POST.get('amount')
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        
        # Create payment
        payment = Payment.objects.create(
            order=order,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status='completed'
        )
        
        # Log payment creation
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='payment_create',
                details=f'Payment of {amount} created for order {order.order_number}',
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        messages.success(request, 'Payment recorded successfully.')
        return redirect('orders:management_order_detail', order_id=order.id)
    
    context = {
        'order': order,
        'payment_methods': Payment.PAYMENT_METHODS,
        'remaining_amount': order.remaining_amount,
    }
    
    return render(request, 'orders/management/payment_add.html', context)

@superuser_required
@login_required
def management_quick_order(request):
    """
    View for handling quick orders from cashier without requiring customer QR scan.
    For customers who don't have smartphones or who don't want to register information.
    """
    tables = Table.objects.filter(is_active=True).order_by('number')
    products = Product.objects.filter(is_active=True, is_available=True).order_by('category__name', 'name')
    categories = Category.objects.filter(is_active=True)
    
    # Handle form submission
    if request.method == 'POST':
        table_id = request.POST.get('table_id')
        product_ids = request.POST.getlist('product_ids[]')
        quantities = request.POST.getlist('quantities[]')
        
        if not table_id or not product_ids or not quantities:
            messages.error(request, 'Please select a table and at least one product.')
            return redirect('orders:management_quick_order')
        
        try:
            table = Table.objects.get(id=table_id)
            
            # Create or get anonymous customer
            anonymous_customer, created = Customer.objects.get_or_create(
                phone_number='anonymous',
                defaults={
                    'user': User.objects.get_or_create(
                        username='anonymous_customer',
                        defaults={'is_active': True}
                    )[0]
                }
            )
            
            # Free the table from any previous orders
            table.free_table()
            
            # Create a new order
            order = Order.objects.create(
                customer=anonymous_customer,
                table=table,
                total_amount=0,
                discount_amount=0,
                final_amount=0,
                status='confirmed'  # Set as confirmed immediately
            )
            
            # Add order items
            for i, product_id in enumerate(product_ids):
                if int(quantities[i]) > 0:  # Only add products with quantity > 0
                    product = Product.objects.get(id=product_id)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=int(quantities[i]),
                        price=product.price
                    )
            
            # Update order totals
            order.total_amount = sum(
                item.price * item.quantity for item in order.items.all()
            )
            order.final_amount = order.total_amount - order.discount_amount
            order.save()
            
            # Create a session for the table and mark it as having an order
            session = table.get_or_create_active_session()
            session.mark_order_submitted()
            
            # Log the quick order creation
            if hasattr(request.user, 'staff'):
                StaffLog.objects.create(
                    staff=request.user.staff,
                    action='quick_order_created',
                    details=f'Quick order {order.order_number} created for table {table.number}',
                    ip_address=request.META.get('REMOTE_ADDR', ''),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            
            messages.success(request, f'Quick order for table {table.number} has been created successfully.')
            return redirect('orders:management_order_detail', order_id=order.id)
            
        except Exception as e:
            messages.error(request, f'Error creating order: {str(e)}')
            return redirect('orders:management_quick_order')
    
    context = {
        'tables': tables,
        'products': products,
        'categories': categories,
    }
    
    return render(request, 'orders/management/quick_order.html', context)
