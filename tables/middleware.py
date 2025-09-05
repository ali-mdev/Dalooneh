from django.shortcuts import redirect
from django.urls import resolve
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse

from .views import check_session, cleanup_cart_data


class TableAuthMiddleware:
    """
    Middleware to ensure users have a valid table session before accessing ordering pages
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Skip middleware for admin pages, management pages, and static files
        if (request.path.startswith('/admin/') or 
            request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            '/management/' in request.path or
            'management_' in request.path):
            return self.get_response(request)
            
        # Skip for the table access endpoints, token validation, and public pages
        if request.path.startswith('/table/') or request.path.startswith('/api/token/') or request.path == '/':
            return self.get_response(request)
            
        # Skip for test QR code page
        if request.path.startswith('/test-qr/'):
            return self.get_response(request)
            
        # Skip for category views - allow public access to all category-related pages
        if '/menu/category' in request.path:
            return self.get_response(request)
            
        # Pages that require table authentication
        restricted_urls = [
            'menu:menu',
            'menu:product_detail',
            'orders:cart',
            'orders:add_to_cart',
            'orders:checkout',
            'orders:order_detail',
        ]
        
        # Check if current URL requires authentication
        try:
            current_url_name = resolve(request.path).url_name
            view_name = resolve(request.path).view_name
            
            # Skip for management views and admin users
            if 'management' in current_url_name or request.user.is_staff or request.user.is_superuser:
                return self.get_response(request)
            
            if current_url_name in restricted_urls or view_name in restricted_urls:
                is_valid, table = check_session(request)
                
                if not is_valid:
                    messages.error(request, "To view the menu and place orders, please first scan the QR code on your table.")
                    return redirect('home')  # Redirect to home page
                
                # Add table to request for easy access in views
                request.table = table
                
        except:
            # If URL resolution fails, just continue
            pass
            
        # Check if session is about to expire
        # This runs before the view is called
        token = request.session.get('table_token')
        if token and not request.user.is_staff and not request.user.is_superuser:
            try:
                from .models import TableSession
                
                session = TableSession.objects.get(token=token)
                
                # If session has expired, clean up cart and session data
                if session.is_expired():
                    print(f"MIDDLEWARE: Session {token} expired, cleaning up cart data")
                    cleanup_cart_data(request, token)
                    
                    # Don't redirect if on the order summary page
                    if 'order-summary' not in request.path:
                        messages.warning(request, 'Your order selection time has expired. Please scan the QR code again.')
                
                # If session is almost expired (within 2 minutes), send a warning
                elif session.expires_at - timezone.now() < timezone.timedelta(minutes=2):
                    # Calculate remaining minutes as a user-friendly number
                    remaining_seconds = (session.expires_at - timezone.now()).total_seconds()
                    remaining_minutes = max(1, int(remaining_seconds / 60))
                    
                    # Add warning to display to the user (if not already on order summary)
                    if 'order-summary' not in request.path:
                        messages.warning(
                            request, 
                            f'Your order selection time will expire in {remaining_minutes} minutes. Please submit your order.'
                        )
            except TableSession.DoesNotExist:
                # Session token not valid, clear session data
                print(f"MIDDLEWARE: Invalid session token {token}, cleaning up cart data")
                cleanup_cart_data(request, token)
                
                # Don't redirect if on the order summary page
                if not request.path.startswith('/menu/'):
                    messages.warning(request, 'Your session is not valid. Please scan the QR code again.')
            except Exception as e:
                print(f"ERROR in TableSessionMiddleware: {str(e)}")
                # No need to handle this further, let the view handle it
                pass
            
        response = self.get_response(request)
        return response 