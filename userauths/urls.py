from django.urls import path
from . import views
from .api_views import RegisterAPIView

app_name = 'userauths'
urlpatterns = [
    path('signup/', views.RegisterView, name='register'), 
    path("login/", views.loginView, name="login"),
    path("logout/", views.logoutView, name="logout"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("agent/dashboard/", views.agent_dashboard, name="agent_dashboard"),
    path("api/register/", RegisterAPIView.as_view(), name="api_register"),
]