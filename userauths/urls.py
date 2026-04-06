from django.urls import path
from . import views

app_name = 'userauths'
urlpatterns = [
    path('signup/', views.RegisterView, name='register'), 
    path("login/", views.loginView, name="login"),
    path("logout/", views.logoutView, name="logout"),
    path("agent/dashboard/", views.agent_dashboard, name="agent_dashboard"),
]