from django.urls import path
from . import views
from .api_views import RegisterAPIView

app_name = 'userauths'
urlpatterns = [
    path('signup/', views.RegisterView, name='register'), 
    path("login/", views.loginView, name="login"),
    path("verify-email-otp/", views.verify_email_otp_view, name="verify_email_otp"),
    path("forgot-password/", views.forgot_password_view, name="forgot_password"),
    path("forgot-password/verify-otp/", views.verify_password_reset_otp_view, name="verify_password_reset_otp"),
    path("change-password/verify-otp/", views.verify_change_password_otp_view, name="verify_change_password_otp"),
    path("tools/smtp-otp-test/", views.smtp_otp_test_view, name="smtp_otp_test"),
    path("logout/", views.logoutView, name="logout"),
    path("change-password/", views.change_password_view, name="change_password"),
    path("verify-email/<uidb64>/<token>/", views.verify_email, name="verify_email"),
    path("agent/dashboard/", views.agent_dashboard, name="agent_dashboard"),
    path("api/register/", RegisterAPIView.as_view(), name="api_register"),
]