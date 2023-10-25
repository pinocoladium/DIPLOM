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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import include, path

from backend.views import (
    BasketView,
    ConfirmEmail,
    LoginClient,
    OrderBuyerView,
    OrderShopView,
    ProfilContacts,
    ProfileClient,
    ProfileShop,
    ShopPricelist,
    ProfileLogout,
    ProfileResetpassword,
    ShopState,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
    path("login/", LoginClient.as_view(), name="login"),
    path("logout/", ProfileLogout.as_view(), name="logout"),
    path("profile/", ProfileClient.as_view(), name="profile"),
    path("profile/email/", ConfirmEmail.as_view(), name="email"),
    path("profile/contacts/", ProfilContacts.as_view(), name="contacts"),
    path("profile/password/", ProfileResetpassword.as_view(), name="password"),
    path("basket/", BasketView.as_view(), name="basket"),
    path("basket/buy", OrderBuyerView.as_view(), name="buy"),
    path("shop/profile/", ProfileShop.as_view(), name="shop"),
    path("shop/profile/state/", ShopState.as_view(), name="state"),
    path("shop/profile/pricelist/", ShopPricelist.as_view(), name="pricelist"),
    path("shop/profile/orders/", OrderShopView.as_view(), name="orders"),
    path("products/", include("backend.urls")),
    path("products/", include("backend.urls")),
]
