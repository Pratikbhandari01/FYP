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
        user = form.save()  # ✅ get the created user instance

        full_name = form.cleaned_data.get("fullname")
        phone = form.cleaned_data.get("phone")

        messages.success(request, f"Welcome {full_name}, your account is successfully created! Please log in.")

        # ✅ create or update profile using the created user (NOT request.user)
        profile, created = Profile.objects.get_or_create(user=user)
        profile.full_name = full_name
        profile.phone = phone
        profile.save()

        return redirect("userauths:login")

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
                print(f"DEBUG: Searching by email for {login_key}")
                user_query = User.objects.get(email=login_key)
            else:
                print(f"DEBUG: Searching by username for {login_key}")
                user_query = User.objects.get(username=login_key)
            
            print(f"DEBUG: Found user: {user_query.username}")
            
            user_auth = authenticate(request, username=user_query.username, password=password)
            print(f"DEBUG: Authenticate result: {user_auth}")

            if user_auth is not None:
                login(request, user_auth)
                messages.success(request, f"Welcome back {user_query.profile.full_name or user_query.username}!")
                return redirect("hotel:index")
            else:
                messages.error(request, "Invalid username/email or password.")
                print("DEBUG: Redirecting back to login due to invalid password")
                return redirect("userauths:login")
        except User.DoesNotExist:
            print("DEBUG: User does not exist")
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