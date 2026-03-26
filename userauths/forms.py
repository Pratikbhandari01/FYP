from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
User = get_user_model()

class UserRegistration(UserCreationForm):
    fullname = forms.CharField(max_length=150, required=True)
    phone = forms.CharField(max_length=15, required=True)

    class Meta:
        model = User
        fields = ["fullname", "username", "email","phone", "password1", "password2"]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user