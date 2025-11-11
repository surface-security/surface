import hashlib
import json
from typing import Any, Literal, Optional

from django.conf import settings
from django.contrib.admin.templatetags.admin_urls import admin_urlname
from django.http import HttpRequest
from django.urls import reverse
from django.utils.http import urlencode


def digital_sizer(num, suffix='B'):
    for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0


def json_hash(obj: dict[str, Any]) -> str:
    """md5 hex digest of json of an object."""
    j = json.dumps(obj, sort_keys=True, indent=2)
    return hashlib.md5(j.encode("utf-8")).hexdigest()  # nosec - md5 not used for security


def array_split(array, parts):
    """
    split an array into `parts` arrays, evenly size
    """
    n = len(array)
    np, nl = divmod(n, parts)
    i = 0
    for p in range(parts if np > 0 else nl):
        s = np + 1 if p < nl else np
        yield array[i : i + s]
        i += s


def admin_reverse(
    obj,
    action: Literal["changelist", "add", "history", "delete", "change"],
    request: Optional[HttpRequest] = None,
    relative: bool = False,
    query_kwargs=None,
):
    if not obj:
        return None

    if action in ["change", "history", "delete"]:
        args = (obj.pk,)
    else:
        args = None

    r = reverse(admin_urlname(obj._meta if hasattr(obj, "_meta") else obj, action), args=args)
    if query_kwargs:
        r += f"?{urlencode(query_kwargs)}"

    if relative:
        return r

    if request:
        return request.build_absolute_uri(r)
    return settings.BASE_HOSTNAME + r
