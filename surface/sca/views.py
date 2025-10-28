import logging
import re

import requests
from django.conf import settings
from django.http HttpResponse, JsonResponse
from django.views.decorators.http import require_GET


logger = logging.getLogger(__name__)


@require_GET
def download_sbom_as_json(request, uuid: str, proj_name: str):
    if not re.match(r"^[a-zA-Z0-9\-:]+$", uuid):
        return HttpResponse("Invalid UUID format", status=400)

    if not re.match(r"^[a-zA-Z0-9\-:_]+$", proj_name):
        return HttpResponse("Invalid project name format", status=400)

    sbom_url = f"{settings.SCA_SBOM_REPO_URL}/v1/sbom/{uuid}"
    try:
        response = requests.get(sbom_url)
        response.raise_for_status()

        page_data = {
            "url": sbom_url,
            "status_code": response.status_code,
            "project_name": proj_name,
            "content": response.json(),
        }

        response = JsonResponse(page_data, json_dumps_params={"indent": 2})
        response["Content-Disposition"] = f"attachment; filename=sbom-{proj_name}.json"
        return response

    except requests.RequestException as e:
        return HttpResponse(f"Error fetching page: {str(e)}", status=500)
