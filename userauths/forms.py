from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Profile
User = get_user_model()

class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    agent_document_photo = forms.ImageField(required=False)

    class Meta:
        model = User
        fields = ["full_name", "username", "email", "phone", "gender", "role"]

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get("role")
        doc = cleaned_data.get("agent_document_photo")
        if role == "agent" and not doc:
            self.add_error("agent_document_photo", "Document photo is required for agent registration.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])

        if user.role == "agent":
            user.agent_approval_status = "pending"
            user.agent_rejection_reason = ""

        if commit:
            # Ensure user + profile updates are committed together or rolled back together.
            with transaction.atomic():
                user.save()

                if user.role == "agent":
                    profile, _ = Profile.objects.get_or_create(user=user)
                    profile.identity_image = self.cleaned_data.get("agent_document_photo")
                    profile.save(update_fields=["identity_image"])

        return user