import logging
import random

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)


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

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send verification email to user_id=%s", user.pk)
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

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send agent approval email to user_id=%s", user.pk)
        return False


def generate_login_otp(length: int = 6) -> str:
    length = max(4, int(length or 6))
    return ''.join(random.choices('0123456789', k=length))


def send_login_otp_email(user, otp_code: str) -> bool:
    if not user or not user.email:
        return False

    subject = "Your NepStay login OTP"
    message = (
        f"Hi {user.full_name or user.username},\n\n"
        "Use the OTP below to complete your NepStay login:\n"
        f"{otp_code}\n\n"
        "This OTP expires in 10 minutes.\n"
        "If you did not attempt to login, please ignore this email and consider changing your password.\n"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send login OTP email to user_id=%s", user.pk)
        return False
