from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.http import JsonResponse


def health(request):
    return JsonResponse({"success": True, "message": "OK", "data": {"status": "healthy"}, "errors": None})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/", include("apps.branches.urls")),
    path("api/v1/", include("apps.hr.urls")),
    path("api/v1/", include("apps.recruitment.urls")),
    path("api/v1/", include("apps.crm.urls")),
    path("api/v1/", include("apps.sales.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.timesheets.urls")),
    path("api/v1/", include("apps.finance.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.reports.urls")),
    path("api/v1/", include("apps.accounts.user_urls")),
    path("api/v1/", include("apps.access_control.urls")),
]



def api_404(request, exception=None):
    return JsonResponse({"success": False, "message": "Not found", "data": None, "errors": None}, status=404)

def api_500(request):
    return JsonResponse({"success": False, "message": "Internal server error", "data": None, "errors": None}, status=500)

handler404 = api_404
handler500 = api_500

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)