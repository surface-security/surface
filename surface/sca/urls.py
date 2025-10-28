from django.urls import path

from sca.views import download_sbom_as_json

app_name = "sca"

urlpatterns = [
    path("download-sbom-json/<str:uuid>/<str:proj_name>/", download_sbom_as_json, name="download_sbom_as_json"),
]
