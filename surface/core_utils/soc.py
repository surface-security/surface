from django.conf import settings
from functools import lru_cache


@lru_cache
def _get_soc_report_function(setting):
    func_str = getattr(settings, setting, None)
    if not func_str:
        raise NotImplementedError(f'{setting} is not defined in your settings.py')

    import importlib

    mod_str, met_str = func_str.rsplit('.', 1)
    mod = importlib.import_module(mod_str)
    return getattr(mod, met_str)


def post_event(
    event_id,
    source,
    event_title,
    brand='ppb',
    severity='Info',
    veris_args=None,
    veris_actor=None,
    veris_actor_args=None,
    veris_action_args=None,
    veris_assets_args=None,
    veris_attribute_args=None,
    veris_discovery_and_response_args=None,
    veris_impact_args=None,
    veris_indicators_args=None,
    veris_ppb_args=None,
    draft=False,
    tags=None,
):
    """
    proxy method to send events to whatever platform SOC is using
    """
    return _get_soc_report_function('SOC_REPORT_FUNCTION')(
        event_id,
        source,
        event_title,
        brand=brand,
        severity=severity,
        veris_args=veris_args,
        veris_actor=veris_actor,
        veris_actor_args=veris_actor_args,
        veris_action_args=veris_action_args,
        veris_assets_args=veris_assets_args,
        veris_attribute_args=veris_attribute_args,
        veris_discovery_and_response_args=veris_discovery_and_response_args,
        veris_impact_args=veris_impact_args,
        veris_indicators_args=veris_indicators_args,
        veris_ppb_args=veris_ppb_args,
        draft=draft,
        tags=tags,
    )


def post_splunk(host: str, index: str, sourcetype: str, data: dict) -> bool:
    """
    proxy method
    """
    return _get_soc_report_function('SOC_SPLUNK_FUNCTION')(host, index, sourcetype, data)


def create_incident(
    brand: str,
    source_id: str,
    source: str,
    title: str,
    family: str,
    alert_body: str,
    severity: str,
    draft: bool = False,
    tags: list[str] = None,
    incident_details: dict = None,
    environment_details: dict = None,
    host_details: dict = None,
    user_details: dict = None,
    ticket_details: dict = None,
    incident_args: dict = None,
):
    """
    proxy method
    """
    return _get_soc_report_function('SOC_INCIDENT_FUNCTION')(
        brand,
        source_id,
        source,
        title,
        family,
        alert_body,
        severity,
        draft=draft,
        tags=tags,
        incident_details=incident_details,
        environment_details=environment_details,
        host_details=host_details,
        user_details=user_details,
        ticket_details=ticket_details,
        incident_args=incident_args,
    )
