from django.shortcuts import redirect, render
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from userauths.models import Profile
from userauths.forms import UserRegistrationForm
from userauths.decorators import agent_required
from userauths.email_utils import send_registration_verification_email
from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from hotel.models import Hotel
from hotel.models import Review

User = get_user_model()

def RegisterView(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
            except (IntegrityError, DatabaseError):
                messages.error(request, "Registration failed. Your account was not created. Please try again.")
                return render(request, "userauths/register.html", {"form": form})

            email_sent = send_registration_verification_email(user, request=request)

            authenticated_user = authenticate(
                request,
                username=user.username,
                password=form.cleaned_data.get("password"),
            )

            if authenticated_user is not None:
                login(request, authenticated_user)
            else:
                messages.warning(request, "Account created, but auto-login failed. Please sign in once.")
                return redirect("userauths:login")

            messages.success(request, f"Welcome {user.full_name or user.username}, your account is successfully created.")
            if email_sent:
                messages.info(request, "A verification email has been sent to your inbox.")
            else:
                messages.warning(request, "Account created, but we could not send your verification email right now.")
            
            if user.role == "agent":
                messages.info(request, "Your agent account is submitted for admin review. Please wait for approval.")
                return redirect("hotel:index")
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
        remember_me = request.POST.get("remember_me")

        try:
            if "@" in login_key:
                user_query = User.objects.get(email=login_key)
            else:
                user_query = User.objects.get(username=login_key)
            
            user_auth = authenticate(request, username=user_query.username, password=password)

            if user_auth is not None:
                login(request, user_auth)

                if remember_me:
                    request.session.set_expiry(1209600)
                else:
                    request.session.set_expiry(0)

                # Get display name safely
                display_name = user_query.full_name or user_query.username
                messages.success(request, f"Welcome back {display_name}!")
                
                if user_auth.role == "agent":
                    if user_auth.agent_approval_status == "pending":
                        messages.warning(request, "Your agent account is pending admin approval.")
                        return redirect("hotel:index")

                    if user_auth.agent_approval_status == "rejected":
                        reject_reason = user_auth.agent_rejection_reason or "Your submitted document could not be approved."
                        messages.error(request, f"Agent account rejected. {reject_reason}")
                        return redirect("hotel:index")

                    return redirect("userauths:agent_dashboard")
                else:
                    return redirect("hotel:index")
            else:
                messages.error(request, "Invalid username/email or password.")
                return redirect("userauths:login")
        except User.DoesNotExist:
            messages.error(request, "User doesn't exist.")
            return redirect("userauths:login")
        
    return render(request, "userauths/Login.html")
        
def logoutView(request):
    login_user = getattr(request, "user", None)
    if login_user and login_user.is_authenticated:
        from django.contrib.auth import logout
        logout(request)
        messages.success(request, "You have been logged out.")
    return redirect("hotel:index")


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        if not user.email_verified:
            user.email_verified = True
            user.save(update_fields=["email_verified"])
            messages.success(request, "Your email has been verified successfully.")
        else:
            messages.info(request, "Your email is already verified.")
    else:
        messages.error(request, "Verification link is invalid or expired.")

    return redirect("hotel:index")

@login_required
@agent_required
def agent_dashboard(request):
    hotels = Hotel.objects.filter(agent=request.user)

    received_reviews = Review.objects.filter(agent=request.user).select_related('hotel', 'user')
    average_rating_received = received_reviews.aggregate(avg=Avg('rating')).get('avg') or 0

    context = {
        'hotels': hotels,
        'received_reviews': received_reviews[:10],
        'received_reviews_count': received_reviews.count(),
        'average_rating_received': round(average_rating_received, 1),
    }
    return render(request, "userauths/agent_dashboard.html", context)