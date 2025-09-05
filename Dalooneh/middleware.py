from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
import re

class ManagementAccessMiddleware:
    """
    Middleware to restrict access to management URLs to superusers only.
    This is an additional security layer besides our view decorators.
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.management_url_pattern = re.compile(r'/management/')
        self.staff_url_pattern = re.compile(r'^/staff/$')  # Only protect main staff index
        
    def __call__(self, request):
        # Check if URL contains 'management' or is main staff index and user is not a superuser
        is_management_url = self.management_url_pattern.search(request.path)
        is_staff_index = self.staff_url_pattern.match(request.path)
        
        if is_management_url or is_staff_index:
            # Skip login page itself to avoid redirect loops
            if request.path == '/management/login/':
                response = self.get_response(request)
                return response
                
            if not request.user.is_authenticated:
                messages.error(request, "You must be logged in to access this section.")
                return redirect(f'/management/login/?next={request.path}')
            
            if not request.user.is_superuser:
                messages.error(request, "Only administrators can access this section.")
                return redirect('home')
        
        response = self.get_response(request)
        return response 