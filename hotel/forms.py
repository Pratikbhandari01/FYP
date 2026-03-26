from django import forms

from hotel.models import Hotel


class ContactForm(forms.Form):
    name = forms.CharField(
        label="Name",
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Your name",
        }),
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={
            "class": "form-control",
            "placeholder": "you@example.com",
        }),
    )
    subject = forms.CharField(
        label="Subject",
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Subject",
        }),
        required=False,
    )
    message = forms.CharField(
        label="Message",
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 5,
            "placeholder": "How can we help you?",
        }),
    )


class HotelForm(forms.ModelForm):
    class Meta:
        model = Hotel
        fields = ["name", "location", "description", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hotel name"}),
            "location": forms.TextInput(attrs={"class": "form-control", "placeholder": "City or area"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Hotel description"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class HotelSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Search by hotel name or location",
            }
        ),
    )
