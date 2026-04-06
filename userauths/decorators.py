from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

def agent_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'agent':
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You are not authorized to view this page.")
            return redirect('hotel:index')
    return wrapper

def customer_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'customer':
            return view_func(request, *args, **kwargs)
        else:
            messages.error(request, "You are not authorized to view this page.")
            return redirect('hotel:index')
    return wrapper
