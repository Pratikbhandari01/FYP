from django.urls import path
from . import views

app_name = 'custom_admin'

urlpatterns = [
    path('', views.admin_panel, name='panel'),
    path('logout/', views.admin_logout, name='logout'),
    path('api/dashboard/', views.api_dashboard, name='api_dashboard'),
    path('api/hotels/', views.api_hotels, name='api_hotels'),
    path('api/rooms/', views.api_rooms, name='api_rooms'),
    path('api/room-types/', views.api_room_types, name='api_room_types'),
    path('api/bookings/', views.api_bookings, name='api_bookings'),
    path('api/users/', views.api_users, name='api_users'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/reviews/', views.api_reviews, name='api_reviews'),
    path('api/<str:model_name>/save/', views.api_save_object, name='api_save_object'),
    path('api/agents/<int:user_id>/status/', views.api_update_agent_status, name='api_update_agent_status'),
    path('api/<str:model_name>/<int:obj_id>/delete/', views.api_delete_object, name='api_delete_object'),
    path('<path:legacy_path>', views.admin_legacy_redirect, name='legacy_redirect'),
]
