import logging
import re

import requests
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def download_sbom_as_json(request, uuid: str, proj_name: str):
    """Download SBOM as JSON file with proper filename and error handling."""
    if not re.match(r"^[a-zA-Z0-9\-:]+$", uuid):
        logger.warning(f"Invalid UUID format: {uuid}")
        return HttpResponse("Invalid UUID format", status=400)

    if not re.match(r"^[a-zA-Z0-9\-:_]+$", proj_name):
        logger.warning(f"Invalid project name format: {proj_name}")
        return HttpResponse("Invalid project name format", status=400)

    sbom_url = f"{settings.SCA_SBOM_REPO_URL}/v1/sbom/{uuid}"
    try:
        response = requests.get(sbom_url, timeout=30)
        response.raise_for_status()

        page_data = {
            "url": sbom_url,
            "status_code": response.status_code,
            "project_name": proj_name,
            "content": response.json(),
        }

    
        json_response = JsonResponse(page_data, json_dumps_params={"indent": 2})
        safe_proj_name = re.sub(r'[^\w\-_\.]', '_', proj_name)
        json_response["Content-Disposition"] = f'attachment; filename="sbom-{safe_proj_name}.json"'
        json_response["Content-Type"] = "application/json; charset=utf-8"
        return json_response

    except requests.Timeout:
        logger.error(f"Timeout fetching SBOM from {sbom_url}")
        return HttpResponse("Request timeout while fetching SBOM", status=504)
    except requests.RequestException as e:
        logger.error(f"Error fetching SBOM from {sbom_url}: {e}")
        return HttpResponse(f"Error fetching SBOM: {str(e)}", status=500)
    except ValueError as e:
        logger.error(f"Invalid JSON response from {sbom_url}: {e}")
        return HttpResponse("Invalid response format", status=500)
