from rest_framework.routers import DefaultRouter

from backend.views import ProductViewSet

router = DefaultRouter()
router.register('all', ProductViewSet)

urlpatterns = router.urls
