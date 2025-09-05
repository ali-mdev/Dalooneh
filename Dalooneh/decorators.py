from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.urls import reverse

def superuser_required(view_func):
    """
    Decorator that checks if the user is a superuser.
    If not, redirects to the home page with an error message.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to access this section.")
            return redirect('home')
        if not request.user.is_superuser:
            messages.error(request, "Only administrators can access this section.")
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view 