from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, ClientViewSet, OpportunityViewSet

router = DefaultRouter()
router.register("leads", LeadViewSet, basename="lead")
router.register("clients", ClientViewSet, basename="client")
router.register("opportunities", OpportunityViewSet, basename="opportunity")
urlpatterns = router.urls