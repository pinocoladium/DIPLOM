from rest_framework.routers import DefaultRouter

from backend.views import ProductsViewSet

router = DefaultRouter()
router.register("all", ProductsViewSet)

urlpatterns = router.urls
