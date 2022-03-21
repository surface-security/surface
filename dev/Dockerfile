FROM --platform=$BUILDPLATFORM ghcr.io/surface-security/compile-requirements:3 as requirements
# merge all requirements.txt files together
# as we bind mount the whole context here, this stage will have cache invalidated on any context changes
# but the remaining stages that only use /requirements_full.txt will not

# TODO: compile-requirements currently merges all requirements.txt found, not just the ones mentioned in the "entry" requirements
# once that is fixed, this Dockerfile needs some attention (ie: mention all entrypoints - _prod and _psql)
RUN --mount=type=bind,target=/tmpapp \
    python /run.py /tmpapp/surface/requirements.txt > /requirements_full.txt

FROM python:3.9-slim-buster as builder

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
        libmariadbclient-dev \
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY --from=requirements /requirements_full.txt .

ARG TARGETPLATFORM
# arm/v7 debian buster has no cryptography wheel available, so it tries to build it (and fails)
# use piwheels wheel repo to avoid building it
RUN [ "$TARGETPLATFORM" != "linux/arm/v7" ] || printf "[global]\nextra-index-url=https://www.piwheels.org/simple" > /etc/pip.conf

RUN pip wheel -w /wheels -r requirements_full.txt

############################################################################

FROM python:3.9-slim-buster as main

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
       libmariadb3 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=requirements /requirements_full.txt .
RUN --mount=type=bind,from=builder,src=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels -r /wheels/requirements_full.txt

WORKDIR /app/
COPY surface surface
WORKDIR /app/surface/
