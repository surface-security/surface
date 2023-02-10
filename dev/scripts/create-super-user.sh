#!/usr/bin/env bash

set -e

cd $(dirname $0)

surface/manage.py createsuperuser --noinput --username admin --email admin@localhost && surface/manage.py changepassword admin
 