from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from datetime import timedelta
import hashlib
from userauths.models import Profile
from userauths.forms import UserRegistrationForm
from userauths.decorators import agent_required
from userauths.email_utils import (
    generate_login_otp,
    send_login_otp_email,
    send_registration_verification_email,
)
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from hotel.models import Booking, Hotel, Review, Room

User = get_user_model()

LOGIN_OTP_SESSION_KEYS = [
    'login_otp_user_id',
    'login_otp_hash',
    'login_otp_expires_at',
    'login_otp_remember_me',
    'login_otp_attempts',
    'login_otp_dev_code',
    'login_otp_backend',
]


def _hash_login_otp(raw_code):
    return hashlib.sha256(f'{raw_code}:{User._meta.label_lower}'.encode('utf-8')).hexdigest()


def _clear_login_otp_session(request):
    for key in LOGIN_OTP_SESSION_KEYS:
        request.session.pop(key, None)


def _queue_login_otp(request, user, remember_me=False, backend_path=''):
    otp_code = generate_login_otp(6)
    expires_at = timezone.now() + timedelta(minutes=10)

    request.session['login_otp_user_id'] = user.id
    request.session['login_otp_hash'] = _hash_login_otp(otp_code)
    request.session['login_otp_expires_at'] = expires_at.isoformat()
    request.session['login_otp_remember_me'] = bool(remember_me)
    request.session['login_otp_attempts'] = 0
    request.session['login_otp_backend'] = backend_path or getattr(user, 'backend', '')

    return otp_code


def _mask_email(email):
    if not email or '@' not in email:
        return email or ''
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '*'
    else:
        masked_local = local[0] + ('*' * (len(local) - 2)) + local[-1]
    return f'{masked_local}@{domain}'


def _post_login_redirect(request, user_auth):
    if user_auth.role == "agent":
        if user_auth.agent_approval_status == "pending":
            messages.warning(request, "Your agent account is pending admin approval.")
            return redirect("hotel:index")

        if user_auth.agent_approval_status == "rejected":
            reject_reason = user_auth.agent_rejection_reason or "Your submitted document could not be approved."
            messages.error(request, f"Agent account rejected. {reject_reason}")
            return redirect("hotel:index")

        return redirect("userauths:agent_dashboard")

    return redirect("hotel:index")

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
                if not user_auth.email:
                    messages.error(request, "This account has no email address. Please contact support to enable OTP login.")
                    return redirect("userauths:login")

                _clear_login_otp_session(request)
                otp_code = _queue_login_otp(
                    request,
                    user_auth,
                    remember_me=bool(remember_me),
                    backend_path=getattr(user_auth, 'backend', ''),
                )
                if not send_login_otp_email(user_auth, otp_code):
                    if settings.DEBUG:
                        request.session['login_otp_dev_code'] = otp_code
                        messages.warning(request, f"SMTP email failed. Dev OTP: {otp_code}")
                        return redirect("userauths:verify_login_otp")

                    _clear_login_otp_session(request)
                    messages.error(request, "Unable to send OTP email right now. Please try again shortly.")
                    return redirect("userauths:login")

                messages.info(request, f"An OTP has been sent to {_mask_email(user_auth.email)}.")
                return redirect("userauths:verify_login_otp")
            else:
                messages.error(request, "Invalid username/email or password.")
                return redirect("userauths:login")
        except User.DoesNotExist:
            messages.error(request, "User doesn't exist.")
            return redirect("userauths:login")
        
    return render(request, "userauths/Login.html")


def verify_login_otp_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    user_id = request.session.get('login_otp_user_id')
    otp_hash = request.session.get('login_otp_hash')
    expires_raw = request.session.get('login_otp_expires_at')

    if not user_id or not otp_hash or not expires_raw:
        messages.warning(request, "Your login OTP session has expired. Please login again.")
        return redirect("userauths:login")

    user = User.objects.filter(pk=user_id).first()
    if not user:
        _clear_login_otp_session(request)
        messages.error(request, "User not found. Please login again.")
        return redirect("userauths:login")

    try:
        expires_at = timezone.datetime.fromisoformat(expires_raw)
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    except ValueError:
        _clear_login_otp_session(request)
        messages.error(request, "Invalid OTP session state. Please login again.")
        return redirect("userauths:login")

    if request.method == 'POST' and request.POST.get('action') == 'resend':
        otp_code = _queue_login_otp(
            request,
            user,
            remember_me=bool(request.session.get('login_otp_remember_me')),
            backend_path=request.session.get('login_otp_backend', ''),
        )
        if send_login_otp_email(user, otp_code):
            request.session.pop('login_otp_dev_code', None)
            messages.success(request, "A new OTP has been sent to your email.")
        elif settings.DEBUG:
            request.session['login_otp_dev_code'] = otp_code
            messages.warning(request, f"SMTP email failed. Dev OTP: {otp_code}")
        else:
            messages.error(request, "Unable to resend OTP right now. Please try again.")
        return redirect('userauths:verify_login_otp')

    if timezone.now() > expires_at:
        _clear_login_otp_session(request)
        messages.error(request, "OTP has expired. Please login again.")
        return redirect("userauths:login")

    if request.method == 'POST':
        submitted = (request.POST.get('otp') or '').strip()
        attempts = int(request.session.get('login_otp_attempts', 0))

        if attempts >= 5:
            _clear_login_otp_session(request)
            messages.error(request, "Too many invalid OTP attempts. Please login again.")
            return redirect("userauths:login")

        if _hash_login_otp(submitted) != otp_hash:
            request.session['login_otp_attempts'] = attempts + 1
            remaining = max(0, 5 - (attempts + 1))
            messages.error(request, f"Invalid OTP. {remaining} attempt(s) remaining.")
            return redirect('userauths:verify_login_otp')

        remember_me = bool(request.session.get('login_otp_remember_me'))
        backend_path = request.session.get('login_otp_backend')
        if not backend_path:
            backend_path = settings.AUTHENTICATION_BACKENDS[0]
        _clear_login_otp_session(request)
        login(request, user, backend=backend_path)
        if remember_me:
            request.session.set_expiry(1209600)
        else:
            request.session.set_expiry(0)

        display_name = user.full_name or user.username
        messages.success(request, f"Welcome back {display_name}!")
        return _post_login_redirect(request, user)

    return render(
        request,
        "userauths/verify_login_otp.html",
        {
            'masked_email': _mask_email(user.email),
            'otp_expiry_minutes': 10,
            'dev_otp': request.session.get('login_otp_dev_code', '') if settings.DEBUG else '',
        },
    )
        
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
    hotels = Hotel.objects.filter(agent=request.user).order_by('-created_at', '-date')
    bookings_qs = Booking.objects.filter(hotel__agent=request.user)
    rooms_qs = Room.objects.filter(hotel__agent=request.user)

    today = timezone.localdate()
    week_days = [today - timedelta(days=offset) for offset in range(6, -1, -1)]

    created_booking_counts = {day: 0 for day in week_days}
    for row in bookings_qs.filter(date__date__gte=week_days[0]).values('date__date').annotate(total=Count('id')):
        day = row.get('date__date')
        if day in created_booking_counts:
            created_booking_counts[day] = row['total']

    checkin_counts = {day: 0 for day in week_days}
    for row in bookings_qs.filter(check_in__gte=week_days[0], check_in__lte=today).values('check_in').annotate(total=Count('id')):
        day = row.get('check_in')
        if day in checkin_counts:
            checkin_counts[day] = row['total']

    received_reviews = Review.objects.filter(agent=request.user).select_related('hotel', 'user')
    average_rating_received = received_reviews.aggregate(avg=Avg('rating')).get('avg') or 0

    total_bookings = bookings_qs.count()
    completed_bookings = bookings_qs.filter(payment_status='completed').count()
    completion_rate = round((completed_bookings / total_bookings) * 100, 1) if total_bookings else 0

    context = {
        'hotels': hotels,
        'total_hotels': hotels.count(),
        'total_rooms': rooms_qs.count(),
        'total_bookings': total_bookings,
        'check_ins_today': bookings_qs.filter(check_in=today).count(),
        'check_outs_today': bookings_qs.filter(check_out=today).count(),
        'completion_rate': completion_rate,
        'chart_labels': [day.strftime('%d %b') for day in week_days],
        'chart_new_bookings': [created_booking_counts[day] for day in week_days],
        'chart_checkins': [checkin_counts[day] for day in week_days],
        'received_reviews': received_reviews[:10],
        'received_reviews_count': received_reviews.count(),
        'average_rating_received': round(average_rating_received, 1),
    }
    return render(request, "userauths/agent_dashboard.html", context)


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('hotel:profile')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'userauths/change_password.html', {'form': form})