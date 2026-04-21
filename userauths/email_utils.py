import logging
import random
import json
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)
_LAST_EMAIL_ERROR = ''


def _set_last_email_error(message: str):
    global _LAST_EMAIL_ERROR
    _LAST_EMAIL_ERROR = (message or '').strip()


def get_last_email_error() -> str:
    return _LAST_EMAIL_ERROR


def _send_via_brevo_api(subject: str, message: str, recipient_email: str) -> bool:
    api_key = (getattr(settings, 'BREVO_API_KEY', '') or '').strip()
    if not api_key:
        return False

    sender_email = (getattr(settings, 'DEFAULT_FROM_EMAIL', '') or '').strip() or (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    if not sender_email:
        sender_email = 'no-reply@nepstay.com'

    payload = {
        'sender': {'email': sender_email},
        'to': [{'email': recipient_email}],
        'subject': subject,
        'textContent': message,
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib_request.Request(
        url='https://api.brevo.com/v3/smtp/email',
        data=data,
        method='POST',
        headers={
            'accept': 'application/json',
            'content-type': 'application/json',
            'api-key': api_key,
        },
    )

    timeout = int(getattr(settings, 'EMAIL_TIMEOUT', 30) or 30)
    try:
        with urllib_request.urlopen(req, timeout=timeout) as response:
            return 200 <= int(getattr(response, 'status', 0)) < 300
    except urllib_error.HTTPError as exc:
        try:
            body = (exc.read() or b'').decode('utf-8', errors='ignore').strip()
        except Exception:
            body = ''
        _set_last_email_error(body or str(exc))
        logger.exception('Brevo API email send failed with HTTP error')
        return False
    except Exception as exc:
        _set_last_email_error(str(exc))
        logger.exception('Brevo API email send failed')
        return False


def _send_plain_email(subject: str, message: str, recipient_email: str) -> bool:
    provider = (getattr(settings, 'EMAIL_PROVIDER', '') or '').strip().lower()
    brevo_api_key = (getattr(settings, 'BREVO_API_KEY', '') or '').strip()

    # If Brevo API key is available, prefer API-only because SMTP may be disabled pending activation.
    if brevo_api_key:
        sent = _send_via_brevo_api(subject, message, recipient_email)
        if sent:
            _set_last_email_error('')
        return sent

    try:
        _set_last_email_error('')
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        return True
    except Exception as exc:
        _set_last_email_error(str(exc))
        # If SMTP fails and Brevo API was not attempted earlier, try it as backup.
        if provider == 'brevo' and _send_via_brevo_api(subject, message, recipient_email):
            _set_last_email_error('')
            return True
        return False


def _build_absolute_url(path: str, request=None) -> str:
    if request is not None:
        return request.build_absolute_uri(path)

    base_url = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    if base_url:
        return f"{base_url}{path}"

    return path


def build_verification_link(user, request=None) -> str:
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_path = reverse("userauths:verify_email", kwargs={"uidb64": uidb64, "token": token})
    return _build_absolute_url(verify_path, request=request)


def send_registration_verification_email(user, request=None) -> bool:
    if not user.email:
        return False

    verify_url = build_verification_link(user, request=request)
    subject = "Verify your NepStay account"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Thanks for registering at NepStay. Please verify your email by clicking the link below:\n"
        f"{verify_url}\n\n"
        "If you did not create this account, you can ignore this email.\n"
    )

    if _send_plain_email(subject, message, user.email):
        return True

    logger.error("Failed to send verification email to user_id=%s: %s", user.pk, get_last_email_error())
    return False


def send_agent_approved_email(user) -> bool:
    if not user.email:
        return False

    subject = "Your NepStay agent account has been approved"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Your agent account has been approved by the NepStay admin team. "
        "You can now log in and access the agent dashboard.\n\n"
        "Best regards,\n"
        "NepStay Team\n"
    )

    if _send_plain_email(subject, message, user.email):
        return True

    logger.error("Failed to send agent approval email to user_id=%s: %s", user.pk, get_last_email_error())
    return False


def generate_otp(length: int = 6) -> str:
    length = max(4, int(length or 6))
    return ''.join(random.choices('0123456789', k=length))


def send_email_verification_otp_email(user, otp_code: str) -> bool:
    if not user or not user.email:
        return False

    subject = "Your NepStay email verification OTP"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Use the OTP below to verify your NepStay account email:\n"
        f"{otp_code}\n\n"
        "This OTP expires in 10 minutes.\n"
        "If you did not create this account, please ignore this email.\n"
    )

    if _send_plain_email(subject, message, user.email):
        return True

    logger.error("Failed to send email verification OTP to user_id=%s: %s", user.pk, get_last_email_error())
    return False


def send_password_change_otp_email(user, otp_code: str) -> bool:
    if not user or not user.email:
        return False

    subject = "Your NepStay password change OTP"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Use the OTP below to continue changing your NepStay password:\n"
        f"{otp_code}\n\n"
        "This OTP expires in 10 minutes.\n"
        "If you did not request this change, please ignore this email.\n"
    )

    if _send_plain_email(subject, message, user.email):
        return True

    logger.error("Failed to send password change OTP to user_id=%s: %s", user.pk, get_last_email_error())
    return False


def send_password_reset_otp_email(user, otp_code: str) -> bool:
    if not user or not user.email:
        return False

    subject = "Your NepStay password reset OTP"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Use the OTP below to reset your NepStay password:\n"
        f"{otp_code}\n\n"
        "This OTP expires in 10 minutes.\n"
        "If you did not request a password reset, please ignore this email.\n"
    )

    if _send_plain_email(subject, message, user.email):
        return True

    logger.error("Failed to send password reset OTP email to user_id=%s: %s", user.pk, get_last_email_error())
    return False
