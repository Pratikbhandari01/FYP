from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib import messages
from userauths.models import Profile
from userauths.forms import UserRegistration

User = get_user_model()

def RegisterView(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    form = UserRegistration(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)  # Don't save yet
        
        full_name = form.cleaned_data.get("fullname")
        phone = form.cleaned_data.get("phone")
        
        # Set full_name on User model
        user.full_name = full_name
        user.phone = phone
        user.save()  # Now save the user

        # Ensure profile exists and update it
        profile, created = Profile.objects.get_or_create(user=user)
        profile.full_name = full_name
        profile.phone = phone
        profile.save()

        messages.success(request, f"Welcome {full_name}, your account is successfully created and you are now logged in.")

        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect("hotel:index")

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