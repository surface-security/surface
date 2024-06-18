#!/usr/bin/env bash

set -e

cd $(dirname $0)

function dexec() {
    docker compose -f docker-compose-in-a-box.yml exec "$@"
}

# migrations
dexec surface ./manage.py migrate

# create local admin (ignore failure as user might already exist)
dexec surface ./manage.py createsuperuser --noinput --username admin --email admin@localhost && dexec surface ./manage.py changepassword admin

# create local "rootbox" (using dockerd service from the docker stack)
cat <<EOF | dexec -T surface ./manage.py shell
from scanners import models
models.Rootbox.objects.get_or_create(name='local', defaults={'ip': 'dockerd', 'location': 'local', 'dockerd_port': 2375, 'dockerd_tls': False})
EOF
# create images for sample scanners
cat <<EOF | dexec -T surface ./manage.py shell
from scanners import models
models.ScannerImage.objects.update_or_create(name='example', defaults={'image': 'ghcr.io/surface-security/scanner-example'})
models.ScannerImage.objects.update_or_create(name='httpx', defaults={'image': 'ghcr.io/surface-security/scanner-httpx'})
models.ScannerImage.objects.update_or_create(name='nmap', defaults={'image': 'ghcr.io/surface-security/scanner-nmap'})
EOF

# create default tags used by default scanner Input
cat <<EOF | dexec -T surface ./manage.py shell
from dns_ips.models import Tag
Tag.objects.update_or_create(name="is_external", defaults={"notes": "Tag used for external DNS and IP assets"})
Tag.objects.update_or_create(name="is_external", defaults={"notes": "Tag used for internal DNS and IP assets"})
EOF

echo done
