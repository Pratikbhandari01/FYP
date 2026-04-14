from django.urls import path
from . import views
from .api_views import RegisterAPIView

app_name = 'userauths'
urlpatterns = [
    path('signup/', views.RegisterView, name='register'), 
    path("login/", views.loginView, name="login"),
    path("login/verify-otp/", views.verify_login_otp_view, name="verify_login_otp"),
    path("logout/", views.logoutView, name="logout"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("agent/dashboard/", views.agent_dashboard, name="agent_dashboard"),
    path("api/register/", RegisterAPIView.as_view(), name="api_register"),
]