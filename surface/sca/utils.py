from typing import Literal

import requests
from cvss import CVSS2, CVSS3
from packageurl import PackageURL
from packaging import version
from requests.adapters import HTTPAdapter

try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry


def cvss_to_severity(cvss_vector: str) -> Literal["None", "Low", "Medium", "High", "Critical"]:
    if cvss_vector.startswith("CVSS:3"):
        cvss = CVSS3(cvss_vector)
    else:
        cvss = CVSS2(cvss_vector)

    return cvss.severities()[0]


def cvss_to_score(cvss_vector: str) -> float:
    if not cvss_vector:
        return 0.0
    if cvss_vector.startswith("CVSS:3"):
        cvss = CVSS3(cvss_vector)
    else:
        cvss = CVSS2(cvss_vector)

    return float(cvss.base_score)


def invert_dict(the_dict: dict) -> dict:
    """Invert a nested dictionary."""

    # based on https://www.geeksforgeeks.org/python-inversion-in-nested-dictionary/
    def extract_path(partial_dict, path_way):
        if not partial_dict:
            yield path_way

        for key in partial_dict:
            for p in extract_path(partial_dict[key], path_way + [key]):
                yield p

    res = {}
    for path in extract_path(the_dict, []):
        front = res
        for ele in path[::-1]:
            if ele not in front:
                front[ele] = {}
            front = front[ele]
    return res


def cleanup_tree(the_dict: dict) -> dict:
    """Replace dictionaries whose values are empty by a list of keys directly in a nested dictionary."""
    for key, values in the_dict.items():
        if isinstance(values, list):
            the_dict[key] = values
        elif all(not v for v in values.values()):
            the_dict[key] = list(values.keys())
        else:
            the_dict[key] = cleanup_tree(values)
    return the_dict


def purl_type_to_fomantic_icon(purl_type: str) -> str:
    """Convert a purl type to a fomantic-ui icon."""
    if purl_type == "maven":
        return "java"
    elif purl_type == "npm":
        return "npm"
    elif purl_type == "nuget":
        return "microsoft"
    elif purl_type == "pypi":
        return "python"
    elif purl_type == "rubygems":
        return "gem"
    elif purl_type == "git":
        return "git"
    elif purl_type == "oci" or purl_type == "docker":
        return "docker"
    elif purl_type == "deb":
        return "linux"
    elif purl_type == "rpm":
        return "linux"  
    elif purl_type == "apk":
        return "linux"
    elif "github" in purl_type:
        return "github"
    elif "gitlab" in purl_type:
        return "gitlab"
    elif "stash" in purl_type or "bitbucket" in purl_type:
        return "bitbucket"
    return "question circle outline"


def only_highest_version_dependencies(purls):
    highest_versions = {}
    for purl_string in purls:
        purl = PackageURL.from_string(purl_string)

        if purl.name and purl.version:
            dependency = f"{purl.namespace}/{purl.name}" if purl.namespace else purl.name

            try:
                purl_version = version.parse(purl.version)
            except version.InvalidVersion:
                highest_versions[dependency] = (purl.version, purl_string)
                continue

            if dependency not in highest_versions:
                highest_versions[dependency] = (purl_version, purl_string)
            else:
                current_version, _ = highest_versions[dependency]
                if not isinstance(current_version, version.Version) or purl_version > current_version:
                    highest_versions[dependency] = (purl_version, purl_string)

    return [purl_string for _, purl_string in highest_versions.values()]


def create_http_session() -> requests.Session:
    """
    Create a requests session with retry strategy and connection pooling.

    Returns:
        A configured requests.Session with retry logic for HTTP errors
        and connection pooling for better performance.
    """
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session
