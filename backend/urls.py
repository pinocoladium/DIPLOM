from rest_framework.routers import DefaultRouter

from backend.views import ProductsViewSet, CategoryView, ShopView

router = DefaultRouter()
router.register("all", ProductsViewSet)
router.register("category/all", CategoryView)
router.register("shop/all", ShopView)

urlpatterns = router.urls
