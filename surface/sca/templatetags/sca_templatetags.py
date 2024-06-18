from django import template

from sca.models import SCAFinding
from sca.utils import purl_type_to_fomantic_icon

register = template.Library()


@register.filter
def purl_icon(purl: str) -> str:
    purl_type = purl.split("/", 1)[0].removeprefix("pkg:")
    return purl_type_to_fomantic_icon(purl_type)


@register.filter
def to_str(value):
    return str(value)


@register.filter
def criticality_to_str(severity):
    severity_mapping = {severity_value: severity_name for severity_value, severity_name in SCAFinding.Severity.choices}
    return severity_mapping.get(severity)


@register.filter
def severity_to_color(severity_level):
    severity_color_mapping = {
        SCAFinding.Severity.INFORMATIVE: "blue",
        SCAFinding.Severity.LOW: "green",
        SCAFinding.Severity.MEDIUM: "yellow",
        SCAFinding.Severity.HIGH: "orange",
        SCAFinding.Severity.CRITICAL: "red",
    }

    return severity_color_mapping.get(severity_level, "black")


@register.filter
def cvss_vector(cvss_vector):
    return "/".join(cvss_vector.split("/")[1:])


@register.filter
def cvss_version(cvss_vector):
    return cvss_vector.split(":")[1].split("/")[0]
