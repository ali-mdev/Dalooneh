from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponse, Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.decorators.cache import cache_page
from django.core.cache import cache
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
import os
import json
from django.views.decorators.http import require_POST, require_GET
import uuid
from Dalooneh.decorators import superuser_required

from .models import Table, TableSession
from staff.models import StaffLog


def table_access(request, table_number):
    """
    Handle table access via QR code with table number
    This endpoint is accessed when a customer scans a QR code
    """
    # Find the table
    table = get_object_or_404(Table, number=table_number, is_active=True)
    
    # Check if there's an existing session token in the request
    old_token = request.session.get('table_token')
    old_table_id = request.session.get('table_id')
    
    # If there's an old session or the table has changed, clean up before creating a new session
    if old_token or (old_table_id and old_table_id != table.id):
        print(f"DEBUG: Table changed or new session - cleaning up old cart data")
        cleanup_cart_data(request, old_token, table.id)
    
    # Free the table if it's occupied (most important part)
    # This ensures that if someone scans the QR again, the previous occupancy is cleared
    table.free_table()
    
    # Create a new session for the initial 12-minute selection period
    session = TableSession.objects.create(table=table)
    
    # Store session information in session cookie
    request.session['table_token'] = str(session.token)  # Convert UUID to string
    request.session['table_number'] = table.number
    request.session['table_id'] = table.id
    
    # Set flag to show phone number modal after redirection
    request.session['show_phone_modal'] = True
    print("DEBUG: Setting show_phone_modal = True")
    
    # Log table access
    if request.user.is_authenticated and hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='table_access',
            details=f'Table {table.number} accessed via QR code',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # Only show success message for regular customers, not staff or superusers
    if not request.user.is_staff and not request.user.is_superuser:
        messages.success(request, f'You have successfully connected to table number {table.number}. Please select your order within 12 minutes.')
    
    # Redirect to home page instead of menu
    return redirect('/')


@cache_page(60)  # Cache for 1 minute
def validate_token(request, token):
    """
    Validate a token directly (used for API validation)
    """
    try:
        session = TableSession.objects.get(token=token)
        
        # Check if session is valid
        if not session.is_active:
            return JsonResponse({
                'valid': False,
                'error': 'This session has been deactivated.'
            })
        
        if session.is_expired():
            # Automatically deactivate expired sessions
            session.deactivate()
            return JsonResponse({
                'valid': False,
                'error': 'The time limit for using this session has expired.',
                'is_expired': True
            })
        
        # Update last used time
        session.update_last_used()
        
        # Get table status
        table_status = {
            'is_occupied': session.table.is_occupied,
            'has_active_order': session.order_submitted,
            'current_order': session.table.current_order.id if session.table.current_order else None,
            'last_order_time': session.table.last_order_time.isoformat() if session.table.last_order_time else None
        }
        
        return JsonResponse({
            'valid': True,
            'table_number': session.table.number,
            'token': token,
            'table_status': table_status,
            'expires_at': session.expires_at.isoformat()
        })
        
    except TableSession.DoesNotExist:
        return JsonResponse({
            'valid': False,
            'error': 'Invalid token.'
        })


def check_session(request):
    """
    Check if user has a valid session
    Returns (is_valid, table_obj)
    """
    token = request.session.get('table_token')
    
    if not token:
        return False, None
    
    try:
        session = TableSession.objects.get(token=token)  # Django will automatically convert string to UUID
        
        # This will automatically deactivate and clean cart if expired
        if session.is_expired():
            print(f"DEBUG: Session {token} has expired in check_session")
            cleanup_cart_data(request, token)
            return False, None
            
        if not session.is_active:
            print(f"DEBUG: Session {token} is not active in check_session")
            cleanup_cart_data(request, token)
            return False, None
            
        # Session is valid, update last_used timestamp
        session.update_last_used()
        return True, session.table
        
    except TableSession.DoesNotExist:
        print(f"DEBUG: Session {token} not found in check_session")
        clear_session_data(request)
        return False, None


def clear_session_data(request):
    """Remove session data related to table"""
    keys = ['table_token', 'table_number', 'table_id']
    for key in keys:
        if key in request.session:
            del request.session[key]


@login_required
def generate_qr_data(request, table_id):
    """Generate a QR code data for a table"""
    # Only staff can generate QR codes
    if not request.user.is_staff:
        raise Http404()
    
    table = get_object_or_404(Table, id=table_id)
    
    # Get the QR code URL (based on table number, not token)
    host = request.get_host()
    qr_url = f"http://{host}{table.get_access_url()}"
    
    # Log QR code generation
    StaffLog.objects.create(
        staff=request.user.staff,
        action='qr_generate',
        details=f'QR code generated for table {table.number}',
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    return HttpResponse(qr_url, content_type='text/plain')


@login_required
def table_status(request, table_id):
    """Get current status of a table"""
    table = get_object_or_404(Table, id=table_id)
    
    # Get active session if exists
    active_session = table.get_active_session()
    
    status = {
        'number': table.number,
        'is_active': table.is_active,
        'is_occupied': table.is_occupied,
        'current_order': table.current_order.id if table.current_order else None,
        'last_order_time': table.last_order_time.isoformat() if table.last_order_time else None,
        'active_session': {
            'token': active_session.token,
            'created_at': active_session.created_at.isoformat(),
            'expires_at': active_session.expires_at.isoformat()
        } if active_session else None
    }
    
    return JsonResponse(status)


def create_test_qr(request):
    """Create a test QR code for demonstration"""
    # Check if there are any tables
    tables = Table.objects.filter(is_active=True)
    
    # If no tables exist, create one
    if not tables.exists():
        table = Table.objects.create(number=1, seats=4)
    else:
        table = tables.first()
    
    # Generate QR code for the table access URL
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Get the absolute URL for testing
    host = request.get_host()
    table_url = f"http://{host}{table.get_access_url()}"
    qr.add_data(table_url)
    qr.make(fit=True)
    
    # Create QR code image
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to media directory
    media_root = settings.MEDIA_ROOT
    os.makedirs(os.path.join(media_root, 'qrcodes'), exist_ok=True)
    qr_path = os.path.join('qrcodes', f'table_{table.number}_qr.png')
    full_path = os.path.join(media_root, qr_path)
    
    img.save(full_path)
    
    # Get URL for template
    qr_url = os.path.join(settings.MEDIA_URL, qr_path)
    
    # Create a new session or get existing one to display token info
    session = table.get_or_create_active_session()
    
    # Log test QR creation
    if request.user.is_authenticated and hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='test_qr_create',
            details=f'Test QR code created for table {table.number}',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
    
    # Pass the info to template
    context = {
        'qr_url': qr_url,
        'table': table,
        'token': session.token,
        'table_url': table_url,
        'expires_at': session.expires_at,
    }
    
    return render(request, 'tables/test_qr.html', context)


def submit_order(request):
    """
    Handle order submission from a table session
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if session is valid
    token = request.session.get('table_token')
    if not token:
        return JsonResponse({'success': False, 'error': 'Invalid session'}, status=400)
    
    try:
        session = TableSession.objects.get(token=token)
        print(f"DEBUG: Processing submit_order for session {session.token}, table {session.table.number}")
        
        # Check if session is valid
        if not session.is_valid():
            return JsonResponse({
                'success': False, 
                'error': 'Session expired or inactive. Please scan the table QR code again.'
            }, status=400)
        
        # Get order data from request
        try:
            order_data = json.loads(request.body)
            print(f"DEBUG: Received order data: {order_data}")
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in submit_order: {str(e)}")
            return JsonResponse({'success': False, 'error': 'Invalid data'}, status=400)
        
        # Import here to avoid circular imports
        from orders.models import Order, OrderItem
        from menu.models import Product
        
        # Example order creation (assuming order_data contains items and necessary info)
        new_order = None
        if 'order_id' in order_data and order_data['order_id']:
            # Update existing order
            try:
                new_order = Order.objects.get(id=order_data['order_id'])
                print(f"DEBUG: Found existing order with ID {new_order.id}")
                
                # Clean up duplicates before confirming the order
                cleanup_duplicates(new_order)
                
                # Change status from pending to confirmed
                if new_order.status == 'pending':
                    new_order.status = 'confirmed'
                    new_order.save(update_fields=['status'])
                    print(f"DEBUG: Updated order {new_order.id} status to 'confirmed'")
                else:
                    print(f"DEBUG: Order {new_order.id} already has status '{new_order.status}', not changing")
            except Order.DoesNotExist:
                print(f"DEBUG: Order with ID {order_data['order_id']} not found")
                new_order = None
        
        if not new_order:
            # Create new order
            from customers.models import Customer
            from django.contrib.auth.models import User
            
            # Try to get customer from various sources
            customer = None
            
            # First, check if we have a customer_id in the session (from phone modal)
            customer_id = request.session.get('customer_id')
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                    print(f"DEBUG: Using customer from session with ID: {customer_id} for submit_order")
                except Customer.DoesNotExist:
                    print(f"DEBUG: Customer with ID {customer_id} not found")
                    customer = None
            
            # Then check if user is authenticated
            if not customer and request.user.is_authenticated and hasattr(request.user, 'customer'):
                customer = request.user.customer
                print(f"DEBUG: Using authenticated customer: {customer.id} for submit_order")
            
            # If still no customer, check if there's a phone number in session
            if not customer and request.session.get('customer_phone'):
                phone_number = request.session.get('customer_phone')
                customer = Customer.objects.filter(phone_number=phone_number).first()
                if customer:
                    print(f"DEBUG: Found customer by phone number: {phone_number} for submit_order")
            
            # If still no customer, create a new one with a generic phone number if we don't have one
            if not customer:
                print("DEBUG: No customer found, creating a temporary one")
                
                # See if we can get the phone number from the order data
                phone_number = order_data.get('phone_number', '')
                
                if not phone_number:
                    # Generate random username if we don't have a phone number
                    username = f"temp_{uuid.uuid4().hex[:8]}"
                    phone_number = f"temp_{uuid.uuid4().hex[:8]}"
                else:
                    # Use phone number as username base
                    username = f"user_{phone_number}"
                
                # Create a new user without password
                user = User.objects.create(
                    username=username,
                    email="",
                    is_active=True
                )
                # Set a non-usable password
                user.set_unusable_password()
                user.save()
                
                # Create a new customer
                customer = Customer.objects.create(
                    user=user,
                    phone_number=phone_number,
                    national_code=None,
                    membership_level="regular", 
                    total_points=0
                )
                
                # Store in session for future use
                request.session['customer_id'] = customer.id
                request.session['customer_phone'] = phone_number
                
                print(f"DEBUG: Created new customer with ID: {customer.id} and phone: {phone_number}")
            
            # Find the existing pending order for this table
            existing_order = Order.objects.filter(
                table=session.table,
                status='pending'
            ).first()
            
            if existing_order:
                # Use the existing order and update its status
                new_order = existing_order
                print(f"DEBUG: Using existing pending order {new_order.id}")
                
                # Update customer if needed
                if new_order.customer != customer:
                    print(f"DEBUG: Updating order customer from {new_order.customer.id} to {customer.id}")
                    new_order.customer = customer
                
                # Set status to confirmed
                if new_order.status == 'pending':
                    new_order.status = 'confirmed'
                    print(f"DEBUG: Setting order status to 'confirmed'")
                
                new_order.save()
                print(f"DEBUG: Updated existing order {new_order.id} status to 'confirmed'")
                
                # Make sure order items are present and correct
                if new_order.items.count() == 0:
                    print(f"WARNING: Order {new_order.id} has no items, but should have items in cart")
            else:
                # Create a new order from scratch
                try:
                    print(f"DEBUG: Creating new order for table {session.table.number}")
                    new_order = Order.objects.create(
                        customer=customer,
                        table=session.table,
                        status='confirmed',  # Set status directly to confirmed
                        total_amount=order_data.get('total_amount', 0),
                        discount_amount=order_data.get('discount_amount', 0),
                        final_amount=order_data.get('final_amount', 0),
                        notes=order_data.get('notes', '')
                    )
                    print(f"DEBUG: Created new order {new_order.id} for customer {customer.id}")
                    
                    # Log the items from order_data for debugging
                    if 'items' in order_data:
                        print(f"DEBUG: Creating {len(order_data['items'])} items for new order")
                        
                        # Create order items
                        for item_data in order_data.get('items', []):
                            try:
                                product = Product.objects.get(id=item_data['product_id'])
                                OrderItem.objects.create(
                                    order=new_order,
                                    product=product,
                                    quantity=item_data['quantity'],
                                    price=item_data['price'],
                                    notes=item_data.get('notes', '')
                                )
                                print(f"DEBUG: Added item product={product.id}, qty={item_data['quantity']}")
                            except Product.DoesNotExist:
                                print(f"ERROR: Product with ID {item_data['product_id']} not found")
                            except Exception as e:
                                print(f"ERROR: Could not create order item: {str(e)}")
                    else:
                        print("WARNING: No items found in order_data")
                except Exception as e:
                    print(f"ERROR: Could not create order: {str(e)}")
                    raise
        
        # Mark session as having submitted an order
        session.mark_order_submitted()
        print(f"DEBUG: Marked session {session.token} as having submitted an order")
        
        # Return success with redirect URL to order summary
        return JsonResponse({
            'success': True,
            'message': 'Order submitted successfully.',
            'order_id': new_order.id,
            'redirect_url': reverse('tables:order_summary_with_id', args=[new_order.id])
        })
        
    except TableSession.DoesNotExist:
        print(f"ERROR: Invalid session token: {token}")
        return JsonResponse({'success': False, 'error': 'Invalid session'}, status=400)
    except Exception as e:
        print(f"ERROR in submit_order: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def complete_order(request, order_id):
    """
    Mark an order as delivered and free up the table
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=403)
    
    try:
        # Import here to avoid circular imports
        from orders.models import Order
        
        order = get_object_or_404(Order, id=order_id)
        
        # Mark order as delivered
        order.status = 'delivered'
        order.save()
        
        # Free up the table
        order.table.free_table()
        
        return JsonResponse({
            'success': True,
            'message': 'Order delivered and table freed.',
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def order_summary(request, order_id=None):
    """
    Display a summary of the submitted order
    If order_id is provided, it displays that specific order
    Otherwise, it tries to load the current order from the session
    """
    # Try to get order ID from URL or from session
    from orders.models import Order, OrderItem
    
    # Case 1: Viewing a specific order (passed in URL)
    if order_id:
        order = get_object_or_404(Order, id=order_id)
    else:
        # Case 2: Check if there's a valid table session
        token = request.session.get('table_token')
        if not token:
            if not request.user.is_staff and not request.user.is_superuser:
                messages.error(request, 'Please scan the table QR code first.')
            return redirect('/')
        
        try:
            session = TableSession.objects.get(token=token)
            # Check if session is valid
            if not session.is_valid():
                if not request.user.is_staff and not request.user.is_superuser:
                    messages.error(request, 'Your session has expired. Please scan the table QR code again.')
                return redirect('/')
            
            # Get the current order for this table
            order = session.table.current_order
            if not order:
                if not request.user.is_staff and not request.user.is_superuser:
                    messages.error(request, 'No order found for this table. Please submit your order first.')
                return redirect('/')
        except TableSession.DoesNotExist:
            if not request.user.is_staff and not request.user.is_superuser:
                messages.error(request, 'Invalid session. Please scan the table QR code first.')
            return redirect('/')
    
    # Prepare context for the template
    context = {
        'order': order,
        'table_number': order.table.number,
        'order_time': order.created_at,
        'items': order.items.all(),
        'total_amount': order.final_amount,
    }
    
    return render(request, 'tables/order_summary.html', context)


def cleanup_duplicates(order):
    """
    Cleanup duplicate items in the order.
    This function checks for items with same product in an order and keeps only one.
    """
    from orders.models import OrderItem
    from django.db.models import Count
    
    # Group by product and find duplicates
    products = OrderItem.objects.filter(order=order).values('product').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    # For each product with duplicates
    for product_data in products:
        product_id = product_data['product']
        
        # Get all items for this product
        items = OrderItem.objects.filter(order=order, product_id=product_id).order_by('id')
        
        if items.count() > 1:
            # Keep the first item, delete the rest
            item_to_keep = items.first()
            # Update quantity to the sum of all quantities
            total_quantity = sum(item.quantity for item in items)
            item_to_keep.quantity = total_quantity
            item_to_keep.save()
            
            # Delete the rest
            items.exclude(id=item_to_keep.id).delete()
            
            print(f"DEBUG: Cleaned up duplicates for product {product_id} in order {order.id}")


@require_POST
def add_to_cart(request):
    """
    Add a product to the cart based on the table session
    This does not require login as it works with table sessions
    """
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        # Validate the table session
        token = request.session.get('table_token')
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Please scan the table QR code first.'
            }, status=400)
        
        try:
            session = TableSession.objects.get(token=token)
            
            # Check if session is valid
            if not session.is_valid():
                return JsonResponse({
                    'success': False,
                    'message': 'Your session has expired. Please scan the table QR code again.'
                }, status=400)
            
            # Get product
            from menu.models import Product
            product = get_object_or_404(Product, id=product_id, is_active=True)
            
            # Import Order models
            from orders.models import Order, OrderItem
            
            # Check if there's an existing pending order for this table
            order = Order.objects.filter(
                table=session.table,
                status='pending'
            ).first()
            
            # If no pending order exists, create a new one
            if not order:
                # Use customer from session or create a new one
                from customers.models import Customer
                from django.contrib.auth.models import User
                
                customer = None
                
                # First, check if we have a customer_id in the session (from phone modal)
                customer_id = request.session.get('customer_id')
                if customer_id:
                    try:
                        customer = Customer.objects.get(id=customer_id)
                        print(f"DEBUG: Using customer from session with ID: {customer_id}")
                    except Customer.DoesNotExist:
                        print(f"DEBUG: Customer with ID {customer_id} not found")
                        customer = None
                
                # Then check if user is authenticated
                if not customer and request.user.is_authenticated and hasattr(request.user, 'customer'):
                    customer = request.user.customer
                    print(f"DEBUG: Using authenticated customer: {customer.id}")
                
                # If still no customer, check if there's a phone number in session
                if not customer and request.session.get('customer_phone'):
                    phone_number = request.session.get('customer_phone')
                    customer = Customer.objects.filter(phone_number=phone_number).first()
                    if customer:
                        print(f"DEBUG: Found customer by phone number: {phone_number}")
                
                # If still no customer, create an anonymous one
                if not customer:
                    print("DEBUG: Creating anonymous customer")
                    anonymous_user, created = User.objects.get_or_create(
                        username='anonymous',
                        defaults={
                            'first_name': 'Anonymous',
                            'last_name': 'Customer',
                            'is_active': True
                        }
                    )
                    
                    customer, created = Customer.objects.get_or_create(
                        user=anonymous_user,
                        defaults={
                            'phone_number': '00000000000',
                            'national_code': '0000000000'
                        }
                    )
                
                # Create new order
                order = Order.objects.create(
                    customer=customer,
                    table=session.table,
                    status='pending',
                    payment_status='pending',
                    total_amount=0,
                    discount_amount=0,
                    final_amount=0
                )
                print(f"DEBUG: Created new order {order.id} for customer {customer.id}")
            
            # Clean up any existing duplicates first
            cleanup_duplicates(order)
            
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
                    defaults={
                        'quantity': quantity,
                        'price': product.price
                    }
                )
                
                if not created:
                    # If item already exists in cart, replace quantity with new value
                    order_item.quantity = quantity
                    order_item.save()
            
            # Update order totals
            # Calculate totals based on items
            total = sum(item.quantity * item.price for item in order.items.all())
            order.total_amount = total
            order.final_amount = total - order.discount_amount
            order.save()
            
            # Get total items count in cart
            cart_count = sum(item.quantity for item in order.items.all())
            
            return JsonResponse({
                'success': True,
                'message': 'Item added to cart',
                'cart_count': cart_count,
                'order_total': float(order.final_amount)
            })
            
        except TableSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session. Please scan the table QR code again.'
            }, status=400)
            
    except Exception as e:
        print(f"ERROR in add_to_cart: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


def view_cart(request):
    """
    Show the cart contents for the current table session
    """
    # Check if user has a valid session
    token = request.session.get('table_token')
    if not token:
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Please scan the table QR code first.')
        return redirect('/')
    
    try:
        session = TableSession.objects.get(token=token)
        
        # Check if session is valid
        if not session.is_valid():
            if not request.user.is_staff and not request.user.is_superuser:
                messages.error(request, 'Your session has expired. Please scan the table QR code again.')
            return redirect('/')
        
        # Import Order models
        from orders.models import Order
        
        # Get pending order for this table
        order = Order.objects.filter(
            table=session.table,
            status='pending'
        ).first()
        
        if not order or order.items.count() == 0:
            if not request.user.is_staff and not request.user.is_superuser:
                messages.info(request, 'Your cart is empty. Please add a product to your cart.')
            return redirect('/')
            
        # Clean up any duplicates before showing the cart
        cleanup_duplicates(order)
        
        # Update order totals (ensure they're accurate)
        total = sum(item.quantity * item.price for item in order.items.all())
        if total != order.total_amount or (total - order.discount_amount) != order.final_amount:
            order.total_amount = total
            order.final_amount = total - order.discount_amount
            order.save(update_fields=['total_amount', 'final_amount'])
            print(f"DEBUG: Updated order totals in view_cart: total={total}, final={order.final_amount}")
        
        # Prepare context
        context = {
            'order': order,
            'items': order.items.all().prefetch_related('product'),
            'table': session.table,
            'session': session
        }
        
        return render(request, 'tables/cart.html', context)
        
    except TableSession.DoesNotExist:
        if not request.user.is_staff and not request.user.is_superuser:
            messages.error(request, 'Invalid session. Please scan the table QR code first.')
        return redirect('/')


@require_POST
def update_cart_item(request, item_id):
    """
    Update quantity of a cart item
    """
    try:
        new_quantity = int(request.POST.get('quantity', 1))
        
        # Check for valid session
        token = request.session.get('table_token')
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session.'
            }, status=400)
        
        try:
            session = TableSession.objects.get(token=token)
            
            # Check if session is valid
            if not session.is_valid():
                return JsonResponse({
                    'success': False,
                    'message': 'Session expired.'
                }, status=400)
            
            # Import Order models
            from orders.models import OrderItem
            
            # Get the order item
            order_item = get_object_or_404(OrderItem, id=item_id)
            
            # Make sure the item belongs to an order for this table
            if order_item.order.table != session.table:
                return JsonResponse({
                    'success': False,
                    'message': 'Unauthorized.'
                }, status=403)
            
            # Update order item quantity
            order_item.quantity = new_quantity
            order_item.save()
            
            # Calculate new totals
            order = order_item.order
            total = sum(item.quantity * item.price for item in order.items.all())
            order.total_amount = total
            order.final_amount = total - order.discount_amount
            order.save()
            
            # Get total items count in cart
            cart_count = sum(item.quantity for item in order.items.all())
            
            return JsonResponse({
                'success': True,
                'message': 'Item quantity updated',
                'new_quantity': new_quantity,
                'new_subtotal': float(order_item.price * new_quantity),
                'item_total': float(order_item.price * new_quantity),
                'order_total': float(order.final_amount),
                'cart_count': cart_count
            })
            
        except TableSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@require_POST
def remove_cart_item(request, item_id):
    """
    Remove an item from the cart
    """
    try:
        # Check for valid session
        token = request.session.get('table_token')
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session.'
            }, status=400)
        
        try:
            session = TableSession.objects.get(token=token)
            
            # Check if session is valid
            if not session.is_valid():
                return JsonResponse({
                    'success': False,
                    'message': 'Session expired.'
                }, status=400)
            
            # Import Order models
            from orders.models import OrderItem
            
            # Get the order item
            order_item = get_object_or_404(OrderItem, id=item_id)
            
            # Make sure the item belongs to an order for this table
            if order_item.order.table != session.table:
                return JsonResponse({
                    'success': False,
                    'message': 'Unauthorized.'
                }, status=403)
            
            # Store the order reference before deleting the item
            order = order_item.order
            
            # Remove the item
            order_item.delete()
            
            # Calculate new totals
            remaining_items = order.items.all()
            if remaining_items:
                total = sum(item.quantity * item.price for item in remaining_items)
                order.total_amount = total
                order.final_amount = total - order.discount_amount
                order.save()
                
                # Get total items count in cart
                cart_count = sum(item.quantity for item in remaining_items)
            else:
                # If no items left, set totals to zero
                order.total_amount = 0
                order.final_amount = 0
                order.save()
                cart_count = 0
            
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart',
                'order_total': float(order.final_amount),
                'empty_cart': not remaining_items.exists(),
                'cart_count': cart_count
            })
            
        except TableSession.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid session.'
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        }, status=500)


@require_GET
def get_cart_count_ajax(request):
    """
    AJAX endpoint to get the current cart count
    """
    # Check if user has a valid session
    token = request.session.get('table_token')
    if not token:
        return JsonResponse({'cart_count': 0})
    
    try:
        session = TableSession.objects.get(token=token)
        
        # Check if session is valid
        if not session.is_valid():
            return JsonResponse({'cart_count': 0})
        
        # Import Order models
        from orders.models import Order
        
        # Get pending order for this table
        order = Order.objects.filter(
            table=session.table,
            status='pending'
        ).first()
        
        if not order or order.items.count() == 0:
            return JsonResponse({'cart_count': 0})
        
        # Get total items count in cart
        cart_count = sum(item.quantity for item in order.items.all())
        
        return JsonResponse({'cart_count': cart_count})
        
    except TableSession.DoesNotExist:
        return JsonResponse({'cart_count': 0})


def cleanup_cart_data(request, token=None, new_table_id=None):
    """
    Clean up cart data when sessions change or expire
    
    Args:
        request: The HTTP request object
        token: The session token to clean up (if None, uses token from request)
        new_table_id: The ID of the new table being accessed (if applicable)
    """
    from orders.models import Order
    
    try:
        # If no token provided, get from request
        if not token:
            token = request.session.get('table_token')
            if not token:
                return
        
        # Find the session
        session = None
        try:
            session = TableSession.objects.get(token=token)
        except TableSession.DoesNotExist:
            print(f"DEBUG: Session with token {token} not found for cleanup")
            clear_session_data(request)
            return
        
        # Get the table from the session
        table = session.table
        
        # If this is a table change, ensure we clean the old table's pending orders
        if new_table_id and table.id != new_table_id:
            print(f"DEBUG: Table changed from {table.id} to {new_table_id}, cleaning up old table's orders")
        
        # Find and clean up any pending orders
        pending_orders = Order.objects.filter(
            table=table,
            status='pending'
        )
        
        if pending_orders.exists():
            print(f"DEBUG: Found {pending_orders.count()} pending orders to clean up")
            for order in pending_orders:
                # Delete all order items
                item_count = order.items.count()
                if item_count > 0:
                    print(f"DEBUG: Deleting {item_count} items from order {order.id}")
                    order.items.all().delete()
                
                # Update order totals
                order.total_amount = 0
                order.final_amount = 0
                order.save(update_fields=['total_amount', 'final_amount'])
                print(f"DEBUG: Reset order {order.id} totals to 0")
        
        # If session is active but expired, deactivate it
        if session.is_active and session.is_expired():
            print(f"DEBUG: Deactivating expired session {session.token}")
            session.deactivate()
        
        # If we're changing tables or sessions, clear session data
        if new_table_id or (session.is_expired() or not session.is_active):
            clear_session_data(request)
            
    except Exception as e:
        print(f"ERROR in cleanup_cart_data: {str(e)}")
        import traceback
        traceback.print_exc()

# Management panel views
@superuser_required
@login_required
def management_dashboard(request):
    """Dashboard for tables management"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    # Get all tables
    tables = Table.objects.all()
    
    # Get count statistics
    table_count = tables.count()
    occupied_tables = [table for table in tables if table.is_occupied]
    occupied_table_count = len(occupied_tables)
    available_table_count = table_count - occupied_table_count
    
    # Get active sessions
    active_sessions = TableSession.objects.filter(is_active=True).select_related('table').order_by('-created_at')[:10]
    
    context = {
        'table_count': table_count,
        'available_table_count': available_table_count,
        'occupied_table_count': occupied_table_count,
        'occupied_tables': occupied_tables[:10],  # Show only first 10
        'active_sessions': active_sessions,
    }
    
    return render(request, 'tables/management/dashboard.html', context)

@superuser_required
@login_required
def management_table_list(request):
    """List all tables with filters"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    seats = request.GET.get('seats', '')
    search = request.GET.get('search', '')
    
    # Start with all tables
    tables_queryset = Table.objects.all()
    
    # Apply filters
    if status == 'active':
        tables_queryset = tables_queryset.filter(is_active=True)
    elif status == 'inactive':
        tables_queryset = tables_queryset.filter(is_active=False)
    
    if seats:
        tables_queryset = tables_queryset.filter(seats=int(seats))
    
    if search:
        tables_queryset = tables_queryset.filter(number__icontains=search)
    
    # Sort tables by number
    tables = list(tables_queryset.order_by('number'))
    
    # Force refresh of table occupation status by checking related orders
    from orders.models import Order
    
    # Get active orders for all tables to refresh their occupied status
    active_order_tables = Order.objects.filter(
        status__in=['pending', 'confirmed', 'preparing', 'ready']
    ).values_list('table_id', flat=True)
    
    # After queryset filtering, filter for occupied/available status
    # This needs to be done in Python since is_occupied is a property
    if status == 'occupied':
        tables = [table for table in tables if table.id in active_order_tables]
    elif status == 'available':
        tables = [table for table in tables if table.id not in active_order_tables]
    
    # Get unique seat options for filter dropdown
    seat_options = Table.objects.values_list('seats', flat=True).distinct().order_by('seats')
    
    context = {
        'tables': tables,
        'status': status,
        'seats': seats,
        'search': search,
        'seat_options': seat_options,
    }
    
    return render(request, 'tables/management/table_list.html', context)

@superuser_required
@login_required
def management_table_detail(request, table_id):
    """View details of a specific table"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    table = get_object_or_404(Table, id=table_id)
    
    # Get table sessions ordered by creation date
    sessions = TableSession.objects.filter(table=table).order_by('-created_at')[:20]
    
    # Get orders for this table
    from orders.models import Order
    orders = Order.objects.filter(table=table).order_by('-created_at')[:10]
    
    context = {
        'table': table,
        'sessions': sessions,
        'orders': orders,
    }
    
    return render(request, 'tables/management/table_detail.html', context)

@superuser_required
@login_required
def management_table_add(request):
    """Add a new table"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    from .forms import TableForm
    
    if request.method == 'POST':
        form = TableForm(request.POST)
        if form.is_valid():
            table = form.save()
            
            # Log table creation - only if user has staff profile
            if hasattr(request.user, 'staff'):
                StaffLog.objects.create(
                    staff=request.user.staff,
                    action='table_create',
                    details=f'Table #{table.number} created',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            # Generate QR code automatically for the new table
            table.generate_qr_code()
            
            messages.success(request, f'Table #{table.number} has been successfully created and its fixed QR code has been generated.')
            
            return redirect('tables:management_table_detail', table_id=table.id)
    else:
        form = TableForm(initial={'is_active': True})
    
    context = {
        'form': form,
    }
    
    return render(request, 'tables/management/table_form.html', context)

@superuser_required
@login_required
def management_table_edit(request, table_id):
    """Edit an existing table"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    from .forms import TableForm
    
    table = get_object_or_404(Table, id=table_id)
    
    if request.method == 'POST':
        form = TableForm(request.POST, instance=table)
        if form.is_valid():
            form.save()
            
            # Log table update - only if user has staff profile
            if hasattr(request.user, 'staff'):
                StaffLog.objects.create(
                    staff=request.user.staff,
                    action='table_update',
                    details=f'Table #{table.number} updated',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
            
            messages.success(request, f'Table #{table.number} information has been successfully updated.')
            return redirect('tables:management_table_detail', table_id=table.id)
    else:
        form = TableForm(instance=table)
    
    context = {
        'form': form,
        'table': table,
    }
    
    return render(request, 'tables/management/table_form.html', context)

@superuser_required
@login_required
def management_table_delete(request, table_id):
    """Delete a table"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    table = get_object_or_404(Table, id=table_id)
    
    # Check if table is occupied
    if table.is_occupied:
        messages.error(request, f'Table #{table.number} is currently occupied and cannot be deleted.')
        return redirect('tables:management_table_detail', table_id=table.id)
    
    if request.method == 'POST':
        # Delete QR code image if exists
        if table.qr_code:
            try:
                if os.path.exists(table.qr_code.path):
                    os.remove(table.qr_code.path)
            except:
                pass
        
        # Log table deletion - only if user has staff profile
        table_number = table.number
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='table_delete',
                details=f'Table #{table_number} deleted',
                ip_address=request.META.get('REMOTE_ADDR')
            )
        
        table.delete()
        messages.success(request, f'Table #{table_number} has been successfully deleted.')
        return redirect('tables:management_table_list')
    
    context = {
        'table': table,
    }
    
    return render(request, 'tables/management/table_confirm_delete.html', context)

@superuser_required
@login_required
def management_table_toggle_status(request, table_id):
    """Toggle table active status"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    table = get_object_or_404(Table, id=table_id)
    
    # Toggle status
    table.is_active = not table.is_active
    table.save()
    
    # Log status change - only if user has staff profile
    if hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='table_status_change',
            details=f'Table #{table.number} status changed to {"active" if table.is_active else "inactive"}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    status_message = 'active' if table.is_active else 'inactive'
    messages.success(request, f'Table #{table.number} status has been changed to {status_message}.')
    
    # Redirect back to table detail
    return redirect('tables:management_table_detail', table_id=table.id)

@superuser_required
@login_required
def management_table_free(request, table_id):
    """Free a table by deactivating active sessions"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    table = get_object_or_404(Table, id=table_id)
    
    # Check if table is occupied
    if not table.is_occupied:
        messages.warning(request, f'Table #{table.number} is currently free.')
        return redirect('tables:management_table_detail', table_id=table.id)
    
    # Free the table
    table.free_table()
    
    # Log table freed - only if user has staff profile
    if hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='table_free',
            details=f'Table #{table.number} freed',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    messages.success(request, f'Table #{table.number} has been successfully freed.')
    
    # Redirect back to table detail
    return redirect('tables:management_table_detail', table_id=table.id)

@superuser_required
@login_required
def management_free_all_tables(request):
    """Free all occupied tables at once"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('/')
    
    # Get all occupied tables
    tables = Table.objects.all()
    
    # Counter for freed tables
    freed_count = 0
    
    # Free each occupied table
    for table in tables:
        if table.is_occupied:
            table.free_table()
            freed_count += 1
    
    # Log action - only if user has staff profile
    if hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='free_all_tables',
            details=f'Freed {freed_count} occupied tables',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    if freed_count > 0:
        messages.success(request, f'{freed_count} occupied tables have been successfully freed.')
    else:
        messages.info(request, 'No occupied tables were found.')
    
    # Redirect back to dashboard
    return redirect('tables:management_dashboard')

@superuser_required
@login_required
def management_generate_qr(request):
    """Generate QR code for a table from management interface"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    table_id = request.GET.get('table_id')
    
    if not table_id:
        messages.error(request, 'Invalid table ID.')
        return redirect('tables:management_table_list')
    
    table = get_object_or_404(Table, id=table_id)
    
    # Check if QR code already exists
    if table.qr_code:
        messages.warning(request, f'Table {table.number} already has a fixed QR code and it cannot be changed.')
    else:
        # Generate QR code
        table.generate_qr_code()
        
        # Log QR code generation - only if user has staff profile
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='qr_generate',
                details=f'QR code generated for table #{table.number}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
        
        messages.success(request, f'Fixed QR code has been successfully generated for table {table.number}.')
    
    # Redirect back to table detail
    return redirect('tables:management_table_detail', table_id=table.id)

@superuser_required
@login_required
def management_generate_all_qr(request):
    """Generate QR codes for all active tables that don't have QR codes yet"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    # Get all active tables without QR codes
    tables = Table.objects.filter(is_active=True, qr_code='')
    
    count = 0
    for table in tables:
        table.generate_qr_code()
        count += 1
    
    # Log QR code generation - only if user has staff profile
    if hasattr(request.user, 'staff'):
        StaffLog.objects.create(
            staff=request.user.staff,
            action='qr_generate_all',
            details=f'QR codes generated for {count} tables that did not have codes',
            ip_address=request.META.get('REMOTE_ADDR')
        )
    
    if count > 0:
        messages.success(request, f'Fixed QR codes have been successfully generated for {count} active tables without codes.')
    else:
        messages.info(request, f'All active tables already have fixed QR codes.')
    
    # Redirect back to table list
    return redirect('tables:management_table_list')

@superuser_required
@login_required
def management_session_list(request):
    """List all table sessions with filters"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    # Get filter parameters
    status = request.GET.get('status', '')
    table_id = request.GET.get('table', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Start with all sessions
    sessions_queryset = TableSession.objects.select_related('table').all()
    
    # Apply filters
    if status == 'active':
        sessions_queryset = sessions_queryset.filter(is_active=True)
    elif status == 'inactive':
        sessions_queryset = sessions_queryset.filter(is_active=False)
    
    if table_id:
        sessions_queryset = sessions_queryset.filter(table_id=table_id)
    
    if date_from:
        sessions_queryset = sessions_queryset.filter(created_at__gte=date_from)
    
    if date_to:
        sessions_queryset = sessions_queryset.filter(created_at__lte=f"{date_to} 23:59:59")
    
    # Sort sessions by creation date (newest first)
    sessions = sessions_queryset.order_by('-created_at')
    
    # Get all tables for filter dropdown
    all_tables = Table.objects.all().order_by('number')
    
    # Filter for expired status
    if status == 'expired':
        # Not efficient, but we need to check is_expired() which is a Python method
        sessions = [session for session in sessions if session.is_expired()]
    
    context = {
        'sessions': sessions,
        'status': status,
        'table_id': table_id,
        'date_from': date_from,
        'date_to': date_to,
        'all_tables': all_tables,
    }
    
    return render(request, 'tables/management/session_list.html', context)

@superuser_required
@login_required
def management_session_detail(request, session_id):
    """View details of a specific session"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    session = get_object_or_404(TableSession, id=session_id)
    
    # Get pending cart items for this session
    from orders.models import Order, OrderItem
    
    # Get active order
    active_order = None
    order_items = []
    pending_cart_items = []
    
    try:
        active_order = Order.objects.filter(
            table=session.table,
            status__in=['pending', 'confirmed', 'preparing', 'ready']
        ).latest('created_at')
        
        if active_order:
            order_items = active_order.items.all()
    except Order.DoesNotExist:
        pass
    
    # If we have an active token but no submitted order, check for cart items
    if session.is_active and not session.order_submitted:
        # Get the latest pending order
        pending_order = Order.objects.filter(
            table=session.table,
            status='pending'
        ).first()
        
        if pending_order:
            pending_cart_items = pending_order.items.all()
    
    context = {
        'session': session,
        'active_order': active_order,
        'order_items': order_items,
        'pending_cart_items': pending_cart_items,
    }
    
    return render(request, 'tables/management/session_detail.html', context)

@superuser_required
@login_required
def management_session_deactivate(request):
    """Deactivate a table session"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('/')
    
    session_id = request.GET.get('session_id')
    
    if not session_id:
        messages.error(request, 'Invalid session ID.')
        return redirect('tables:management_session_list')
    
    session = get_object_or_404(TableSession, id=session_id)
    
    # If session is already inactive, show a warning
    if not session.is_active:
        messages.warning(request, f'Session for table {session.table.number} has already been deactivated.')
    else:
        # Deactivate session
        session.deactivate()
        
        # Log session deactivation - only if user has staff profile
        if hasattr(request.user, 'staff'):
            StaffLog.objects.create(
                staff=request.user.staff,
                action='session_deactivate',
                details=f'Session {session_id} deactivated for table #{session.table.number}',
                ip_address=request.META.get('REMOTE_ADDR')
            )
        
        messages.success(request, f'Session for table {session.table.number} has been successfully deactivated.')
    
    # Handle return path
    return_to = request.GET.get('return_to', '')
    table_id = request.GET.get('table_id', '')
    
    if return_to == 'detail' and table_id:
        return redirect('tables:management_table_detail', table_id=table_id)
    elif return_to == 'detail':
        return redirect('tables:management_session_detail', session_id=session.id)
    else:
        return redirect('tables:management_session_list')
