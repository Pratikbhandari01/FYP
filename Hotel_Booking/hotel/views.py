from django.shortcuts import render
from hotel.models import HotelGallery, HotelFeatures, Hotelfaqs, RoomType,ActivityLog,Hotel,Booking


# Create your views here.
def index(request):
    hotels = Hotel.objects.filter(status="live")
    context = {
        'Hotels': hotels
    }
    return render(request, 'hotel/index.html', context)


def rooms(request):
    hotels = Hotel.objects.filter(status="live")
    context = {
        "hotels": hotels,
    }
    return render(request, 'hotel/Rooms.html', context)