from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from .models import Customer, Discount, CustomerRating
from .forms import CustomerRegistrationForm, CustomerProfileForm, CustomerRatingForm, ManagementCustomerForm, ManagementCustomerRatingForm, ManagementDiscountForm
from staff.models import StaffLog
from django.contrib.auth.models import User
from orders.models import Order
import uuid
from Dalooneh.decorators import superuser_required

def register(request):
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            customer = Customer.objects.create(
                user=user,
                phone_number=form.cleaned_data.get('phone_number'),
                national_code=None,
                birth_date=form.cleaned_data.get('birth_date')
            )
            login(request, user)
            messages.success(request, 'Registration completed successfully.')
            return redirect('customers:profile')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'customers/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful.')
            return redirect('customers:profile')
        else:
            messages.error(request, 'Username or password is incorrect.')
    
    return render(request, 'customers/login.html')

@login_required
def profile(request):
    customer = request.user.customer
    
    if request.method == 'POST':
        form = CustomerProfileForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('customers:profile')
    else:
        form = CustomerProfileForm(instance=customer)
    
    # Get customer statistics
    stats = {
        'total_orders': customer.total_orders,
        'total_spent': customer.total_spent,
        'average_rating': customer.ratings.aggregate(Avg('rating'))['rating__avg'] or 0,
        'membership_level': customer.get_membership_level_display(),
        'total_points': customer.total_points
    }
    
    return render(request, 'customers/profile.html', {
        'form': form,
        'customer': customer,
        'stats': stats
    })

@login_required
def order_history(request):
    customer = request.user.customer
    orders = customer.orders.all().order_by('-created_at')
    
    # Get order statistics
    stats = {
        'total_orders': orders.count(),
        'total_spent': sum(order.final_amount for order in orders),
        'average_order_value': sum(order.final_amount for order in orders) / orders.count() if orders.exists() else 0
    }
    
    return render(request, 'customers/order_history.html', {
        'orders': orders,
        'stats': stats
    })

@login_required
def discount_list(request):
    customer = request.user.customer
    active_discounts = customer.discounts.filter(
        is_active=True,
        valid_from__lte=timezone.now(),
        valid_to__gte=timezone.now()
    )
    
    # Get membership benefits
    membership_benefits = {
        'regular': ['5% discount on special occasions'],
        'silver': ['10% discount on special occasions', 'Birthday gift'],
        'gold': ['15% discount on special occasions', 'Birthday gift', 'Free shipping'],
        'platinum': ['20% discount on special occasions', 'Birthday gift', 'Free shipping', 'Access to special menu']
    }
    
    return render(request, 'customers/discount_list.html', {
        'discounts': active_discounts,
        'membership_benefits': membership_benefits.get(customer.membership_level, [])
    })

@login_required
def rate_order(request, order_id):
    customer = request.user.customer
    order = get_object_or_404(Order, id=order_id, customer=customer)
    
    # Check if order is delivered
    if order.status != 'delivered':
        messages.error(request, 'You can only rate delivered orders.')
        return redirect('customers:order_history')
    
    # Check if already rated
    if hasattr(order, 'rating'):
        messages.error(request, 'You have already rated this order.')
        return redirect('customers:order_history')
    
    if request.method == 'POST':
        form = CustomerRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.customer = customer
            rating.order = order
            rating.save()
            
            # Add points based on rating
            points = rating.rating * 10  # 10 points per star
            customer.add_points(points)
            
            messages.success(request, 'Your rating has been submitted successfully.')
            return redirect('customers:order_history')
    else:
        form = CustomerRatingForm()
    
    return render(request, 'customers/rate_order.html', {
        'form': form,
        'order': order
    })

@login_required
def membership_details(request):
    customer = request.user.customer
    
    # Get membership requirements
    requirements = {
        'silver': 1000,
        'gold': 5000,
        'platinum': 10000
    }
    
    # Calculate progress to next level
    next_level = None
    points_needed = 0
    for level, points in requirements.items():
        if customer.total_points < points:
            next_level = level
            points_needed = points - customer.total_points
            break
    
    return render(request, 'customers/membership_details.html', {
        'customer': customer,
        'next_level': next_level,
        'points_needed': points_needed,
        'requirements': requirements
    })

def submit_phone_number(request):
    """Handle phone number submission from modal"""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        print(f"DEBUG: Received phone number: {phone_number}")
        
        # Validate phone number - Improved validation
        if not phone_number:
            return JsonResponse({
                'success': False,
                'message': 'Please enter your phone number'
            })
        
        # Remove any spaces or special characters
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Validate length after cleanup
        if len(phone_number) < 10 or len(phone_number) > 15:
            return JsonResponse({
                'success': False,
                'message': 'The entered number is not valid. Please enter the number correctly'
            })
        
        try:
            # Check if a customer with this phone number already exists
            customer = Customer.objects.filter(phone_number=phone_number).first()
            
            if not customer:
                print(f"DEBUG: Creating new customer for number: {phone_number}")
                # Create a new user with a simple username based on phone number
                username = f"user_{phone_number}"
                
                # Create user without password
                user = User.objects.create(
                    username=username,
                    email="",
                    # No password required, just create the user
                    # We'll set a non-usable password
                    is_active=True
                )
                # Set a non-usable password
                user.set_unusable_password()
                user.save()
                
                try:
                    # Create customer with phone number only
                    customer = Customer.objects.create(
                        user=user,
                        phone_number=phone_number,
                        national_code=None,  # No national code needed
                        membership_level="regular",  # Set default membership level
                        total_points=0
                    )
                    
                    print(f"DEBUG: New customer created with ID: {customer.id}")
                except Exception as create_error:
                    # If customer creation fails, delete the user we just created
                    user.delete()
                    print(f"ERROR in customer creation: {str(create_error)}")
                    return JsonResponse({
                        'success': False,
                        'message': 'There was a problem connecting to the server. Please try again'
                    })
                
                # Associate with the current session
                request.session['customer_id'] = customer.id
                request.session['is_new_customer'] = True
                
                is_new = True
                message = 'Your number has been registered successfully. Thank you for choosing Dalooneh'
            else:
                print(f"DEBUG: Existing customer found with ID: {customer.id}")
                # Store customer ID in session
                request.session['customer_id'] = customer.id
                request.session['is_new_customer'] = False
                
                is_new = False
                message = 'Welcome. Your number is registered in the system'
            
            # Store the customer's phone number in the session for easy access
            request.session['customer_phone'] = phone_number
            
            # If there's an active table session, associate the customer with it
            if 'table_token' in request.session:
                from tables.models import TableSession
                try:
                    session = TableSession.objects.get(token=request.session['table_token'])
                    print(f"DEBUG: Associating customer with table session: {session.token}")
                    # You can add additional logic here to associate the customer with the table session
                except TableSession.DoesNotExist:
                    print("DEBUG: No active table session found")
            
            # Get previous orders if customer exists and has orders
            previous_orders = []
            if not is_new:
                from orders.models import Order
                orders = Order.objects.filter(customer=customer).order_by('-created_at')[:3]
                if orders.exists():
                    previous_orders = [
                        {
                            'id': order.id, 
                            'number': order.order_number, 
                            'date': order.created_at.strftime('%Y-%m-%d'), 
                            'total': float(order.final_amount)
                        } 
                        for order in orders
                    ]
            
            return JsonResponse({
                'success': True,
                'customer_id': customer.id,
                'customer_phone': phone_number,
                'is_new': is_new,
                'message': message,
                'previous_orders': previous_orders
            })
        except Exception as e:
            print(f"ERROR: Error creating/finding customer: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'There was a problem connecting to the server. Please try again'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request'
    })

# Management Panel Views
@superuser_required
@login_required
def management_dashboard(request):
    """Dashboard view for the customers management panel."""
    total_customers = Customer.objects.count()
    active_customers = Customer.objects.filter(is_active=True).count()
    
    # Get membership level statistics
    membership_stats = Customer.objects.values('membership_level').annotate(
        count=Count('id')
    ).order_by('membership_level')
    
    # Get average rating
    avg_rating = CustomerRating.objects.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Get active discounts
    active_discounts = Discount.objects.filter(is_active=True).count()
    
    context = {
        'total_customers': total_customers,
        'active_customers': active_customers,
        'membership_stats': membership_stats,
        'avg_rating': avg_rating,
        'active_discounts': active_discounts,
    }
    return render(request, 'customers/management/dashboard.html', context)

@superuser_required
@login_required
def management_customer_list(request):
    """List all customers for management."""
    # Get filter parameters
    membership = request.GET.get('membership')
    is_active = request.GET.get('is_active')
    search_query = request.GET.get('q')
    
    # Base queryset
    customers = Customer.objects.all().select_related('user').order_by('-created_at')
    
    # Apply filters
    if membership:
        customers = customers.filter(membership_level=membership)
    if is_active == 'true':
        customers = customers.filter(is_active=True)
    elif is_active == 'false':
        customers = customers.filter(is_active=False)
    if search_query:
        customers = customers.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(national_code__icontains=search_query)
        )
    
    return render(request, 'customers/management/customer_list.html', {
        'customers': customers,
        'filters': {
            'membership': membership,
            'is_active': is_active,
            'search_query': search_query
        }
    })

@superuser_required
@login_required
def management_customer_detail(request, customer_id):
    """Show customer details."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    # Get related data
    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    ratings = CustomerRating.objects.filter(customer=customer).order_by('-created_at')
    discounts = Discount.objects.filter(customer=customer).order_by('-created_at')
    
    context = {
        'customer': customer,
        'orders': orders,
        'ratings': ratings,
        'discounts': discounts,
    }
    return render(request, 'customers/management/customer_detail.html', context)

@superuser_required
@login_required
def management_customer_add(request):
    """Add a new customer."""
    if request.method == 'POST':
        form = ManagementCustomerForm(request.POST)
        if form.is_valid():
            # Create a new user
            from django.contrib.auth.models import User
            user = User.objects.create(
                username=form.cleaned_data['phone_number'],  # Use phone as username
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
            )
            # Set a default password (they can reset it later)
            user.set_password('changeme123')
            user.save()
            
            # Create customer linked to user
            customer = Customer(
                user=user,
                phone_number=form.cleaned_data['phone_number'],
                national_code=form.cleaned_data['national_code'],
                address=form.cleaned_data['address'],
                birth_date=form.cleaned_data['birth_date'],
                membership_level=form.cleaned_data['membership_level'],
                is_active=form.cleaned_data['is_active'],
            )
            customer.save()
            
            messages.success(request, 'Customer created successfully.')
            return redirect('customers:management_customer_list')
    else:
        form = ManagementCustomerForm()
    
    return render(request, 'customers/management/customer_form.html', {
        'form': form,
        'title': 'Add New Customer'
    })

@superuser_required
@login_required
def management_customer_edit(request, customer_id):
    """Edit an existing customer."""
    customer = get_object_or_404(Customer, id=customer_id)
    
    if request.method == 'POST':
        form = ManagementCustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, 'Customer information updated successfully.')
            return redirect('customers:management_customer_detail', customer_id=customer.id)
    else:
        form = ManagementCustomerForm(instance=customer)
    
    return render(request, 'customers/management/customer_form.html', {
        'form': form,
        'customer': customer,
        'title': 'Edit Customer Information'
    })

@superuser_required
@login_required
def management_rating_list(request):
    """List all customer ratings."""
    # Get filter parameters
    customer_id = request.GET.get('customer')
    min_rating = request.GET.get('min_rating')
    max_rating = request.GET.get('max_rating')
    
    # Base queryset
    ratings = CustomerRating.objects.all().select_related('customer__user', 'order').order_by('-created_at')
    
    # Apply filters
    if customer_id:
        ratings = ratings.filter(customer_id=customer_id)
    if min_rating:
        ratings = ratings.filter(rating__gte=min_rating)
    if max_rating:
        ratings = ratings.filter(rating__lte=max_rating)
    
    # Get all customers for filter dropdown
    customers = Customer.objects.all().select_related('user')
    
    return render(request, 'customers/management/rating_list.html', {
        'ratings': ratings,
        'customers': customers,
        'filters': {
            'customer_id': customer_id,
            'min_rating': min_rating,
            'max_rating': max_rating
        }
    })

@superuser_required
@login_required
def management_discount_list(request):
    """List all discounts."""
    # Get filter parameters
    customer_id = request.GET.get('customer')
    is_active = request.GET.get('is_active')
    search_query = request.GET.get('q')
    
    # Base queryset
    discounts = Discount.objects.all().select_related('customer__user').order_by('-created_at')
    
    # Apply filters
    if customer_id:
        discounts = discounts.filter(customer_id=customer_id)
    if is_active == 'true':
        discounts = discounts.filter(is_active=True)
    elif is_active == 'false':
        discounts = discounts.filter(is_active=False)
    if search_query:
        discounts = discounts.filter(code__icontains=search_query)
    
    # Get all customers for filter dropdown
    customers = Customer.objects.all().select_related('user')
    
    return render(request, 'customers/management/discount_list.html', {
        'discounts': discounts,
        'customers': customers,
        'filters': {
            'customer_id': customer_id,
            'is_active': is_active,
            'search_query': search_query
        }
    })

@superuser_required
@login_required
def management_discount_add(request):
    """Add a new discount."""
    if request.method == 'POST':
        form = ManagementDiscountForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Discount code created successfully.')
            return redirect('customers:management_discount_list')
    else:
        form = ManagementDiscountForm()
    
    return render(request, 'customers/management/discount_form.html', {
        'form': form,
        'title': 'Add New Discount Code'
    })

@superuser_required
@login_required
def management_discount_edit(request, discount_id):
    """Edit an existing discount."""
    discount = get_object_or_404(Discount, id=discount_id)
    
    if request.method == 'POST':
        form = ManagementDiscountForm(request.POST, instance=discount)
        if form.is_valid():
            form.save()
            messages.success(request, 'Discount code updated successfully.')
            return redirect('customers:management_discount_list')
    else:
        form = ManagementDiscountForm(instance=discount)
    
    return render(request, 'customers/management/discount_form.html', {
        'form': form,
        'discount': discount,
        'title': 'Edit Discount Code'
    })

@superuser_required
@login_required
def management_discount_delete(request, discount_id):
    """Delete a discount."""
    discount = get_object_or_404(Discount, id=discount_id)
    
    if request.method == 'POST':
        discount.delete()
        messages.success(request, 'Discount code deleted successfully.')
        return redirect('customers:management_discount_list')
    
    return render(request, 'customers/management/discount_confirm_delete.html', {
        'discount': discount
    })
