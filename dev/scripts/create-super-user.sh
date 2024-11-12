#!/usr/bin/env bash

set -e

PROJECT_ROOT=$(dirname $(dirname $(dirname $0)))

cd "${PROJECT_ROOT}"
python surface/manage.py createsuperuser --noinput --username admin --email admin@localhost && \
python surface/manage.py changepassword admin