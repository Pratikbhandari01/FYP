from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib import messages
from userauths.models import Profile
from userauths.forms import UserRegistrationForm
from userauths.decorators import agent_required
from django.contrib.auth.decorators import login_required
from hotel.models import Hotel

User = get_user_model()

def RegisterView(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome {user.full_name or user.username}, your account is successfully created.")
            
            if user.role == "agent":
                return redirect("userauths:agent_dashboard")
            else:
                return redirect("hotel:index")
    else:
        form = UserRegistrationForm()

    return render(request, "userauths/register.html", {"form": form})

def loginView(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")
    

    if request.method == "POST":
        login_key = request.POST.get("username")
        password = request.POST.get("password")

        try:
            if "@" in login_key:
                user_query = User.objects.get(email=login_key)
            else:
                user_query = User.objects.get(username=login_key)
            
            user_auth = authenticate(request, username=user_query.username, password=password)

            if user_auth is not None:
                login(request, user_auth)
                # Get display name safely
                display_name = user_query.full_name or user_query.username
                messages.success(request, f"Welcome back {display_name}!")
                
                if user_auth.role == "agent":
                    return redirect("userauths:agent_dashboard")
                else:
                    return redirect("hotel:index")
            else:
                messages.error(request, "Invalid username/email or password.")
                return redirect("userauths:login")
        except User.DoesNotExist:
            messages.error(request, "User doesn't exist.")
            return redirect("userauths:login")
        
    return render(request, "userauths/login.html")
        
def logoutView(request):
    login_user = getattr(request, "user", None)
    if login_user and login_user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("hotel:index")

@login_required
@agent_required
def agent_dashboard(request):
    hotels = Hotel.objects.filter(agent=request.user)
    context = {
        'hotels': hotels
    }
    return render(request, "userauths/agent_dashboard.html", context)