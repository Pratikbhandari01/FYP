from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.db import DatabaseError, IntegrityError
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from datetime import timedelta
from types import SimpleNamespace
import hashlib
from userauths.models import Profile
from userauths.forms import PasswordReauthForm, UserRegistrationForm
from userauths.decorators import agent_required
from userauths.email_utils import (
    generate_otp,
    get_last_email_error,
    send_email_verification_otp_email,
    send_password_change_otp_email,
    send_password_reset_otp_email,
)
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Avg, Count
from hotel.models import Booking, Hotel, Review, Room

User = get_user_model()

PASSWORD_RESET_OTP_SESSION_KEYS = [
    'password_reset_user_id',
    'password_reset_otp_hash',
    'password_reset_otp_expires_at',
    'password_reset_otp_attempts',
    'password_reset_otp_dev_code',
]

CHANGE_PASSWORD_OTP_SESSION_KEYS = [
    'change_password_user_id',
    'change_password_otp_hash',
    'change_password_otp_expires_at',
    'change_password_otp_attempts',
    'change_password_otp_dev_code',
]

EMAIL_VERIFY_OTP_SESSION_KEYS = [
    'email_verify_user_id',
    'email_verify_otp_hash',
    'email_verify_otp_expires_at',
    'email_verify_otp_attempts',
    'email_verify_otp_dev_code',
]


def _hash_password_reset_otp(raw_code):
    return hashlib.sha256(f'reset:{raw_code}:{User._meta.label_lower}'.encode('utf-8')).hexdigest()


def _clear_password_reset_otp_session(request):
    for key in PASSWORD_RESET_OTP_SESSION_KEYS:
        request.session.pop(key, None)


def _hash_change_password_otp(raw_code):
    return hashlib.sha256(f'change:{raw_code}:{User._meta.label_lower}'.encode('utf-8')).hexdigest()


def _clear_change_password_otp_session(request):
    for key in CHANGE_PASSWORD_OTP_SESSION_KEYS:
        request.session.pop(key, None)


def _hash_email_verify_otp(raw_code):
    return hashlib.sha256(f'verify:{raw_code}:{User._meta.label_lower}'.encode('utf-8')).hexdigest()


def _clear_email_verify_otp_session(request):
    for key in EMAIL_VERIFY_OTP_SESSION_KEYS:
        request.session.pop(key, None)


def _queue_email_verify_otp(request, user):
    # Email verification OTP no longer used
    return None


def _start_email_verification_flow(request, user):
    _clear_email_verify_otp_session(request)
    otp_code = _queue_email_verify_otp(request, user)

    if send_email_verification_otp_email(user, otp_code):
        messages.info(request, f'Verification OTP sent to {_mask_email(user.email)}.')
        return redirect('userauths:verify_email_otp')

    _clear_email_verify_otp_session(request)
    messages.error(request, _smtp_failure_message())
    return redirect('userauths:login')


def _queue_password_reset_otp(request, user):
    otp_code = generate_otp(6)
    expires_at = timezone.now() + timedelta(minutes=10)

    request.session['password_reset_user_id'] = user.id
    request.session['password_reset_otp_hash'] = _hash_password_reset_otp(otp_code)
    request.session['password_reset_otp_expires_at'] = expires_at.isoformat()
    request.session['password_reset_otp_attempts'] = 0

    return otp_code


def _queue_change_password_otp(request, user):
    otp_code = generate_otp(6)
    expires_at = timezone.now() + timedelta(minutes=10)

    request.session['change_password_user_id'] = user.id
    request.session['change_password_otp_hash'] = _hash_change_password_otp(otp_code)
    request.session['change_password_otp_expires_at'] = expires_at.isoformat()
    request.session['change_password_otp_attempts'] = 0

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


def _email_smtp_ready():
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        return True
    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower()
    brevo_api_key = (getattr(settings, 'BREVO_API_KEY', '') or '').strip()
    return provider == 'brevo' and bool(brevo_api_key)


def _smtp_failure_message():
    last_error = (get_last_email_error() or '').strip()
    if last_error:
        lower = last_error.lower()
        if 'not yet activated' in lower:
            return (
                'Unable to send OTP email. Brevo says your SMTP account is not yet activated. '
                'Please contact contact@sendinblue.com for activation.'
            )
        if 'username and password not accepted' in lower:
            return 'Unable to send OTP email. SMTP credentials were rejected by provider. Please verify login/key.'
        return f'Unable to send OTP email. Provider response: {last_error}'

    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower()
    if provider == 'brevo':
        return (
            'Unable to send OTP email. Your Brevo SMTP account is likely not activated yet. '
            'Please activate SMTP in Brevo or contact contact@sendinblue.com.'
        )
    if provider == 'gmail':
        return (
            'Unable to send OTP email. For Gmail, set a valid 16-character App Password '
            'in EMAIL_HOST_PASSWORD.'
        )
    return 'Unable to send OTP email. Please check SMTP settings and try again.'


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

            messages.success(request, f"Welcome {user.full_name or user.username}, your account is successfully created.")
            if user.role == "agent":
                messages.info(request, "Your agent account is submitted for admin review. Please wait for approval.")

            # Auto-verify email on registration (no OTP required)
            user.email_verified = True
            user.save(update_fields=['email_verified'])
            
            return redirect('userauths:login')
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

                display_name = user_auth.full_name or user_auth.username
                messages.success(request, f"Welcome back {display_name}!")
                return _post_login_redirect(request, user_auth)
            else:
                messages.error(request, "Invalid username/email or password.")
                return redirect("userauths:login")
        except User.DoesNotExist:
            messages.error(request, "User doesn't exist.")
            return redirect("userauths:login")
        
    return render(request, "userauths/Login.html")


def forgot_password_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    if request.method == 'POST':
        login_key = (request.POST.get('login_key') or '').strip()

        if not login_key:
            messages.error(request, 'Please enter your username or email.')
            return redirect('userauths:forgot_password')

        if not _email_smtp_ready():
            messages.error(request, 'SMTP is not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env.')
            return redirect('userauths:forgot_password')

        if '@' in login_key:
            user = User.objects.filter(email__iexact=login_key).first()
        else:
            user = User.objects.filter(username__iexact=login_key).first()

        if not user:
            messages.error(request, 'No account found for the provided username/email.')
            return redirect('userauths:forgot_password')

        if not user.email:
            messages.error(request, 'This account has no email address. Please contact support.')
            return redirect('userauths:forgot_password')

        _clear_password_reset_otp_session(request)
        otp_code = _queue_password_reset_otp(request, user)

        if send_password_reset_otp_email(user, otp_code):
            messages.success(request, f'OTP sent to {_mask_email(user.email)}.')
            return redirect('userauths:verify_password_reset_otp')

        _clear_password_reset_otp_session(request)
        messages.error(request, _smtp_failure_message())
        return redirect('userauths:forgot_password')

    return render(request, 'userauths/forgot_password.html')


def verify_email_otp_view(request):
    # Email verification after registration doesn't require OTP
    # Just redirect to login
    messages.info(request, 'Account created successfully. Please log in.')
    return redirect('userauths:login')


def verify_password_reset_otp_view(request):
    if request.user.is_authenticated:
        messages.warning(request, "You are already logged in.")
        return redirect("hotel:index")

    user_id = request.session.get('password_reset_user_id')
    otp_hash = request.session.get('password_reset_otp_hash')
    expires_raw = request.session.get('password_reset_otp_expires_at')

    if not user_id or not otp_hash or not expires_raw:
        messages.warning(request, 'Your password reset session has expired. Please request a new OTP.')
        return redirect('userauths:forgot_password')

    user = User.objects.filter(pk=user_id).first()
    if not user:
        _clear_password_reset_otp_session(request)
        messages.error(request, 'User not found. Please try again.')
        return redirect('userauths:forgot_password')

    try:
        expires_at = timezone.datetime.fromisoformat(expires_raw)
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    except ValueError:
        _clear_password_reset_otp_session(request)
        messages.error(request, 'Invalid password reset session. Please try again.')
        return redirect('userauths:forgot_password')

    if timezone.now() > expires_at:
        _clear_password_reset_otp_session(request)
        messages.error(request, 'OTP has expired. Please request a new one.')
        return redirect('userauths:forgot_password')

    if request.method == 'POST' and request.POST.get('action') == 'resend':
        otp_code = _queue_password_reset_otp(request, user)
        if send_password_reset_otp_email(user, otp_code):
            messages.success(request, 'A new OTP has been sent to your email.')
        else:
            messages.error(request, _smtp_failure_message())
        return redirect('userauths:verify_password_reset_otp')

    if request.method == 'POST':
        submitted_otp = (request.POST.get('otp') or '').strip()
        new_password = request.POST.get('new_password') or ''
        confirm_password = request.POST.get('confirm_password') or ''
        attempts = int(request.session.get('password_reset_otp_attempts', 0))

        if attempts >= 5:
            _clear_password_reset_otp_session(request)
            messages.error(request, 'Too many invalid OTP attempts. Please request a new OTP.')
            return redirect('userauths:forgot_password')

        if _hash_password_reset_otp(submitted_otp) != otp_hash:
            request.session['password_reset_otp_attempts'] = attempts + 1
            remaining = max(0, 5 - (attempts + 1))
            messages.error(request, f'Invalid OTP. {remaining} attempt(s) remaining.')
            return redirect('userauths:verify_password_reset_otp')

        if len(new_password) < 8:
            messages.error(request, 'New password must be at least 8 characters long.')
            return redirect('userauths:verify_password_reset_otp')

        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('userauths:verify_password_reset_otp')

        user.set_password(new_password)
        user.save(update_fields=['password'])
        _clear_password_reset_otp_session(request)
        messages.success(request, 'Your password has been reset successfully. Please login.')
        return redirect('userauths:login')

    return render(
        request,
        'userauths/verify_password_reset_otp.html',
        {
            'masked_email': _mask_email(user.email),
            'otp_expiry_minutes': 10,
        },
    )


@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordReauthForm(request.user, request.POST)
        if form.is_valid():
            if not request.user.email:
                messages.error(request, 'This account has no email address. Please contact support.')
                return redirect('userauths:change_password')

            if not _email_smtp_ready():
                messages.error(request, 'SMTP is not configured. Set EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env.')
                return redirect('userauths:change_password')

            _clear_change_password_otp_session(request)
            otp_code = _queue_change_password_otp(request, request.user)

            if send_password_change_otp_email(request.user, otp_code):
                messages.success(request, f'OTP sent to {_mask_email(request.user.email)}. Continue to change your password.')
                return redirect('userauths:verify_change_password_otp')

            _clear_change_password_otp_session(request)
            messages.error(request, _smtp_failure_message())
            return redirect('userauths:change_password')

        messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordReauthForm(request.user)

    return render(request, 'userauths/change_password.html', {'form': form})


@login_required
def verify_change_password_otp_view(request):
    user_id = request.session.get('change_password_user_id')
    otp_hash = request.session.get('change_password_otp_hash')
    expires_raw = request.session.get('change_password_otp_expires_at')

    if not user_id or not otp_hash or not expires_raw:
        messages.warning(request, 'Your password change session has expired. Please start again.')
        return redirect('userauths:change_password')

    user = User.objects.filter(pk=user_id).first()
    if not user:
        _clear_change_password_otp_session(request)
        messages.error(request, 'User not found. Please start again.')
        return redirect('userauths:change_password')

    try:
        expires_at = timezone.datetime.fromisoformat(expires_raw)
        if timezone.is_naive(expires_at):
            expires_at = timezone.make_aware(expires_at, timezone.get_current_timezone())
    except ValueError:
        _clear_change_password_otp_session(request)
        messages.error(request, 'Invalid password change session. Please start again.')
        return redirect('userauths:change_password')

    if timezone.now() > expires_at:
        _clear_change_password_otp_session(request)
        messages.error(request, 'OTP has expired. Please start the password change again.')
        return redirect('userauths:change_password')

    form = SetPasswordForm(user, request.POST or None)
    form.fields['new_password1'].widget.attrs.update({
        'class': 'auth-input',
        'placeholder': 'New Password',
        'autocomplete': 'new-password',
    })
    form.fields['new_password2'].widget.attrs.update({
        'class': 'auth-input',
        'placeholder': 'Confirm New Password',
        'autocomplete': 'new-password',
    })

    if request.method == 'POST' and request.POST.get('action') == 'resend':
        otp_code = _queue_change_password_otp(request, user)
        if send_password_change_otp_email(user, otp_code):
            messages.success(request, 'A new OTP has been sent to your email.')
        else:
            messages.error(request, _smtp_failure_message())
        return redirect('userauths:verify_change_password_otp')

    if request.method == 'POST':
        submitted_otp = (request.POST.get('otp') or '').strip()
        attempts = int(request.session.get('change_password_otp_attempts', 0))

        if attempts >= 5:
            _clear_change_password_otp_session(request)
            messages.error(request, 'Too many invalid OTP attempts. Please start again.')
            return redirect('userauths:change_password')

        if _hash_change_password_otp(submitted_otp) != otp_hash:
            request.session['change_password_otp_attempts'] = attempts + 1
            remaining = max(0, 5 - (attempts + 1))
            messages.error(request, f'Invalid OTP. {remaining} attempt(s) remaining.')
            return redirect('userauths:verify_change_password_otp')

        if form.is_valid():
            updated_user = form.save()
            update_session_auth_hash(request, updated_user)
            _clear_change_password_otp_session(request)
            messages.success(request, 'Your password has been changed successfully.')
            return redirect('hotel:profile')

        messages.error(request, 'Please correct the password fields below.')

    return render(
        request,
        'userauths/verify_change_password_otp.html',
        {
            'masked_email': _mask_email(user.email),
            'otp_expiry_minutes': 10,
            'form': form,
        },
    )


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def smtp_otp_test_view(request):
    context = {
        'selected_type': 'password_change',
        'recipient_email': '',
    }

    if request.method == 'POST':
        recipient_email = (request.POST.get('recipient_email') or '').strip()
        otp_type = (request.POST.get('otp_type') or 'email_verify').strip()

        context['selected_type'] = otp_type
        context['recipient_email'] = recipient_email

        if not recipient_email:
            messages.error(request, 'Please enter a recipient email address.')
            return render(request, 'userauths/smtp_otp_test.html', context)

        otp_code = generate_otp(6)

        dummy_user = SimpleNamespace(
            pk='smtp-test',
            email=recipient_email,
            full_name='SMTP Test User',
            username='smtp_test',
        )

        sender_map = {
            'password_change': send_password_change_otp_email,
            'password_reset': send_password_reset_otp_email,
            'email_verify': send_email_verification_otp_email,
        }
        send_func = sender_map.get(otp_type, send_email_verification_otp_email)

        if send_func(dummy_user, otp_code):
            messages.success(request, f'OTP test email sent successfully to {recipient_email}.')
        else:
            messages.error(request, _smtp_failure_message())

    return render(request, 'userauths/smtp_otp_test.html', context)
        
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

