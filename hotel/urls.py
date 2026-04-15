from django.urls import path
from hotel import views

app_name = 'hotel'
urlpatterns = [
    path('', views.index, name='index'),
    path('hotels/', views.HotelListView.as_view(), name='hotel_list'),
    path('rooms/', views.rooms, name='rooms'),
    path('rooms/ajax/<int:hotel_id>/', views.rooms_by_hotel_ajax, name='rooms_by_hotel_ajax'),
    path('hotels/<int:hotel_id>/', views.hotel_detail, name='hotel_detail'),
    path('hotels/<int:hotel_id>/reviews/add/', views.add_review, name='add_review'),
    path('hotels/<int:hotel_id>/reviews/delete/', views.delete_review, name='delete_review'),
    path('rooms/book/<int:room_id>/', views.book_room, name='book_room'),
    path('payment/khalti/callback/', views.khalti_payment_callback, name='khalti_payment_callback'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('profile/', views.profile_view, name='profile'),
    # API endpoints
    path('api/room-types/', views.room_types_api, name='room_types_api'),
    # Agent hotel management
    path('agent/hotels/', views.AgentHotelListView.as_view(), name='agent_hotel_list'),
    path('agent/hotels/create/', views.CreateHotelView.as_view(), name='create_hotel'),
    path('agent/hotels/<int:pk>/update/', views.UpdateHotelView.as_view(), name='update_hotel'),
    path('agent/hotels/<int:pk>/delete/', views.DeleteHotelView.as_view(), name='delete_hotel'),
    path('agent/hotels/<int:hotel_id>/room-types/', views.room_type_list, name='room_type_list'),
    path('agent/hotels/<int:hotel_id>/room-types/add/', views.add_room_type, name='add_room_type'),
    path('agent/hotels/<int:hotel_id>/room-types/<int:room_type_id>/update/', views.update_room_type, name='update_room_type'),
    path('agent/hotels/<int:hotel_id>/room-types/<int:room_type_id>/delete/', views.delete_room_type, name='delete_room_type'),
    path('agent/hotels/<int:hotel_id>/add-room/', views.add_room, name='add_room'),
    # Customer bookings
    path('customer/bookings/', views.customer_bookings, name='customer_bookings'),
]