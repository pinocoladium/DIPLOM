"""
URL configuration for marketplace project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path

from backend.views import (ConfirmEmail, LoginClient, Pricelist, ProfileClient,
                           ProfileShop, logout_view, state_change_view)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", LoginClient.as_view()),
    path("logout/", logout_view),
    path("profile/", ProfileClient.as_view()),
    path("profile/email/", ConfirmEmail.as_view()),
    path("profile/shop/", ProfileShop.as_view()),
    path("profile/shop/state/", state_change_view),
    path("profile/shop/pricelist/", Pricelist.as_view()),
    path("products/", include("backend.urls")),
    # path("products/{slug:slug}", include("backend.urls")),
]
