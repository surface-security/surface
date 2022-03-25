FROM --platform=$BUILDPLATFORM ghcr.io/surface-security/compile-requirements:4 as requirements
# merge all requirements.txt files together
# as we bind mount the whole context here, this stage will have cache invalidated on any context changes
# but the remaining stages that only use /requirements_full.txt will not

RUN --mount=type=bind,target=/tmpapp \
    python /run.py /tmpapp/surface/requirements.txt \
                   /tmpapp/surface/requirements_prod.txt \
                   /tmpapp/surface/requirements_psql.txt > /requirements_full.txt

FROM python:3.9-slim-buster as builder

# RUN apt-get update \
#  && apt-get install --no-install-recommends -y \
#         libmariadbclient-dev \
#         build-essential \
#         libldap2-dev \
#         libsasl2-dev \
#         git \
#  && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY --from=requirements /requirements_full.txt .

ARG TARGETPLATFORM
# arm/v7 debian buster has no cryptography wheel available, so it tries to build it (and fails)
# use piwheels wheel repo to avoid building it
RUN [ "$TARGETPLATFORM" != "linux/arm/v7" ] || printf "[global]\nextra-index-url=https://www.piwheels.org/simple" > /etc/pip.conf

RUN pip wheel -w /wheels -r requirements_full.txt

############################################################################

FROM python:3.9-slim-buster as main

# FIXME: piwheels does not include libs
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
       libpq5 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=requirements /requirements_full.txt .
# FIXME: delete psycopg lib in wheels, as we already installed the lib before - if piwheels includes libs, clean this up
RUN --mount=type=bind,from=builder,src=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels -r /wheels/requirements_full.txt \
 && find /usr/local/lib/ -name psycopg2_binary.libs | xargs rm -fr

WORKDIR /app/
COPY surface surface
WORKDIR /app/surface/
