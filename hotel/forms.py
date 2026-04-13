from django import forms

from hotel.models import Hotel, Review, Room, RoomType


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
        fields = ["name", "description", "image", "address", "mobile", "email", "status"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hotel name"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Hotel description"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "address": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hotel address"}),
            "mobile": forms.TextInput(attrs={"class": "form-control", "placeholder": "Hotel mobile"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Hotel email"}),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


class RoomForm(forms.ModelForm):
    class Meta:
        model = Room
        fields = ['room_type', 'room_number', 'price', 'availability']
        widgets = {
            'room_type': forms.Select(attrs={'class': 'form-control'}),
            'room_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 101'}),
            'price': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class RoomTypeForm(forms.ModelForm):
    class Meta:
        model = RoomType
        fields = ["name", "description", "price", "no_of_beds", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., Deluxe Room"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4, "placeholder": "Describe this room type"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "placeholder": "e.g., 3000"}),
            "no_of_beds": forms.NumberInput(attrs={"class": "form-control", "min": "1"}),
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


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(attrs={'class': 'form-select'}),
            'comment': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Share your experience with this hotel...',
                }
            ),
        }
