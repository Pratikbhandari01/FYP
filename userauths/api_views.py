import json
import re

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from userauths.email_utils import send_registration_verification_email


User = get_user_model()


def _normalize_role(raw_role: str) -> str:
    role = (raw_role or "guest").strip().lower()
    if role in {"guest", "customer"}:
        return "customer"
    if role == "agent":
        return "agent"
    return ""


def _build_username(email: str) -> str:
    local_part = (email.split("@", 1)[0] or "user").lower().strip()
    base = re.sub(r"[^a-z0-9._-]", "", local_part) or "user"
    candidate = base
    counter = 1
    while User.objects.filter(username=candidate).exists():
        counter += 1
        candidate = f"{base}{counter}"
    return candidate


@method_decorator(csrf_exempt, name="dispatch")
class RegisterAPIView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

        # Allow both JSON and form-encoded payloads.
        data = payload if isinstance(payload, dict) and payload else request.POST

        full_name = (data.get("name") or data.get("full_name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        role = _normalize_role(data.get("role"))

        errors = {}
        if not full_name:
            errors["name"] = ["Name is required."]
        if not email:
            errors["email"] = ["Email is required."]
        elif User.objects.filter(email__iexact=email).exists():
            errors["email"] = ["An account with this email already exists."]
        if not password:
            errors["password"] = ["Password is required."]
        elif len(password) < 8:
            errors["password"] = ["Password must be at least 8 characters long."]
        if not role:
            errors["role"] = ["Role must be Guest or Agent."]

        if errors:
            return JsonResponse({"errors": errors}, status=400)

        username = _build_username(email)

        try:
            with transaction.atomic():
                user = User(
                    full_name=full_name,
                    email=email,
                    username=username,
                    role=role,
                )
                if role == "agent":
                    user.agent_approval_status = "pending"
                    user.agent_rejection_reason = ""

                # Use Django's password hashing system.
                user.set_password(password)
                user.save()

            send_registration_verification_email(user, request=request)
        except IntegrityError:
            return JsonResponse(
                {"errors": {"email": ["An account with this email already exists."]}},
                status=400,
            )

        return JsonResponse(
            {
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "name": user.full_name,
                    "email": user.email,
                    "username": user.username,
                    "role": "Guest" if user.role == "customer" else "Agent",
                },
            },
            status=201,
        )
