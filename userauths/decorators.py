from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

def agent_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'agent' and request.user.agent_approval_status == 'approved':
            return view_func(request, *args, **kwargs)
        else:
            if request.user.is_authenticated and request.user.role == 'agent' and request.user.agent_approval_status == 'pending':
                messages.warning(request, "Your agent account is pending admin approval.")
            elif request.user.is_authenticated and request.user.role == 'agent' and request.user.agent_approval_status == 'rejected':
                reason = request.user.agent_rejection_reason or "Your submitted document could not be approved."
                messages.error(request, f"Agent account rejected. {reason}")
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
