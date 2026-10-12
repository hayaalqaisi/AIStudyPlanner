from django.urls import path

from accounts.views.login_view import login_view
from accounts.views.logout_view import logout_view
from accounts.views.registration_view import registration_view


app_name = "accounts"

urlpatterns = [
    path("register/", registration_view, name="register"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
]