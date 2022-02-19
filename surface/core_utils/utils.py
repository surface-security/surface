import json
import hashlib
from typing import Any


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
