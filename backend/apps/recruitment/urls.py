from rest_framework.routers import DefaultRouter
from .views import VacancyViewSet, CandidateViewSet, ApplicationViewSet

router = DefaultRouter()
router.register("vacancies", VacancyViewSet, basename="vacancy")
router.register("candidates", CandidateViewSet, basename="candidate")
router.register("recruitment-applications", ApplicationViewSet, basename="recruitment-application")
urlpatterns = router.urls