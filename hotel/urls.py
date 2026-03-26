from django.urls import path
from hotel import views

app_name = 'hotel'
urlpatterns = [
    path('', views.index, name='index'),
    path('hotels/', views.HotelListView.as_view(), name='hotel_list'),
    path('rooms/', views.rooms, name='rooms'),
    path('rooms/ajax/<int:hotel_id>/', views.rooms_by_hotel_ajax, name='rooms_by_hotel_ajax'),
    path('rooms/book/<int:room_id>/', views.book_room, name='book_room'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
]