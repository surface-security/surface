import base64
import os

import docker
from django.conf import settings
from django.db.models.query import QuerySet

from scanners import models

from . import _docker


def settings_to_file(b64content, filepath, mode=0o600):
    if b64content is None or not filepath:
        raise Exception('missing file path')
    if not os.path.isfile(filepath) or os.stat(filepath).st_size == 0:
        with open(filepath, 'wb') as file:
            file.write(base64.b64decode(b64content))
            os.chmod(filepath, mode)
        return True
    return False


def get_docker_client(ip, port=80, use_tls=True):
    if use_tls:
        settings_to_file(settings.SCANNERS_DOCKER_CA_CERT, settings.SCANNERS_DOCKER_CA_CERT_PATH)
        settings_to_file(settings.SCANNERS_DOCKER_CLIENT_KEY, settings.SCANNERS_DOCKER_CLIENT_KEY_PATH)
        settings_to_file(settings.SCANNERS_DOCKER_CLIENT_CERT, settings.SCANNERS_DOCKER_CLIENT_CERT_PATH)
        tlsconfig = docker.tls.TLSConfig(
            ca_cert=settings.SCANNERS_DOCKER_CA_CERT_PATH,
            client_cert=(settings.SCANNERS_DOCKER_CLIENT_CERT_PATH, settings.SCANNERS_DOCKER_CLIENT_KEY_PATH),
            verify=settings.SCANNERS_DOCKER_CA_CERT_PATH,
        )
    else:
        tlsconfig = False

    client = _docker.OurDockerClient(
        base_url=f'tcp://{ip}:{port}',
        tls=tlsconfig,
    )
    # set _auth_configs to avoid need of config.json on disk or passing the info on every method
    client.api._auth_configs = docker.auth.AuthConfig({'auths': settings.SCANNERS_REGISTRY_AUTH})
    return client


def check_scanners_in_box(box, all=False, sparse=True):
    client = get_docker_client(box.ip, port=box.dockerd_port, use_tls=box.dockerd_tls)
    for c in client.containers.list(sparse=sparse, all=all):
        name = c.attrs.get('Names', [''])[0].lstrip('/') if sparse else c.name
        yield name, c


def check_scanners(rootboxes=None):
    """
    :param rootboxes: show scanners only for the rootboxes in this list. Default is every rootbox.
    :return: tuple with box name and running scanner list
    """
    if isinstance(rootboxes, QuerySet):
        boxes = rootboxes
    else:
        boxes = models.Rootbox.objects.all()
        if rootboxes:
            if isinstance(rootboxes[0], models.Rootbox):
                # forget that queryset
                boxes = rootboxes
            else:
                boxes = boxes.filter(name__in=rootboxes)

    out = []

    for box in boxes:
        cs = []
        for c_name, c in check_scanners_in_box(box):
            cs.append(
                {
                    'id': c.short_id,
                    'name': c_name,
                    'image': c.attrs.get('Image'),
                    'created_at': c.attrs.get('Created'),
                    'status': c.attrs.get('Status'),
                    'state': c.status,
                }
            )
        out.append((box.name, cs))

    return out
