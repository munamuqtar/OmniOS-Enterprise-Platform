from django.urls import path
from rest_framework.routers import DefaultRouter
from .lookups import UserLookupView
from .views import UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
urlpatterns = [path("lookups/users/", UserLookupView.as_view()), *router.urls]