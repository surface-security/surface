from django.apps import AppConfig
from django.conf import settings

APP_SETTINGS = dict(
    PUBLIC_KEY_PATH=None,
    PRIVATE_KEY_PATH=None,
    REGISTRY_AUTH={},
    DOCKER_CA_CERT=None,
    DOCKER_CA_CERT_PATH=None,
    DOCKER_CLIENT_KEY=None,
    DOCKER_CLIENT_KEY_PATH=None,
    DOCKER_CLIENT_CERT=None,
    DOCKER_CLIENT_CERT_PATH=None,
    PROXY_USERNAME=None,
    PROXY_PASSWORD=None,
    HELPER_IMAGE='ghcr.io/surface-security/scanner-helper',
    HELPER_IMAGE_TAG='1',
    PROXY_IMAGE='ghcr.io/surface-security/scanner-proxy',
    PROXY_IMAGE_TAG='latest',
)


class ScannersConfig(AppConfig):
    name = 'scanners'

    def ready(self):
        super().ready()
        for k, v in APP_SETTINGS.items():
            _k = 'SCANNERS_%s' % k
            if not hasattr(settings, _k):
                setattr(settings, _k, v)

        self.module.autodiscover()
