from django.urls import path
from hotel import views

app_name = 'hotel'
urlpatterns = [
    path('', views.index, name='index'),
    path('hotels/', views.HotelListView.as_view(), name='hotel_list'),
    path('rooms/', views.rooms, name='rooms'),
    path('rooms/ajax/<int:hotel_id>/', views.rooms_by_hotel_ajax, name='rooms_by_hotel_ajax'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('rooms/book/<int:room_id>/', views.book_room, name='book_room'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile_view, name='profile'),
    # API endpoints
    path('api/room-types/', views.room_types_api, name='room_types_api'),
]