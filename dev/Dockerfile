FROM --platform=$BUILDPLATFORM ghcr.io/surface-security/compile-requirements:4 as requirements
# merge all requirements.txt files together
# as we bind mount the whole context here, this stage will have cache invalidated on any context changes
# but the remaining stages that only use /requirements_full.txt will not

RUN --mount=type=bind,target=/tmpapp \
    python /run.py /tmpapp/surface/requirements.txt \
                   /tmpapp/surface/requirements_prod.txt \
                   /tmpapp/surface/requirements_psql.txt > /requirements_full.txt

FROM python:3.9-slim-buster as builder-armv7
# FIXME: armv7 debian buster misses several wheels such as cryptography and postgres
# piwheels.org is not reliable but can't take 1h to compile cryptography...
RUN printf "[global]\nextra-index-url=https://www.piwheels.org/simple" > /etc/pip.conf

FROM python:3.9-slim-buster as builder-amd64
FROM python:3.9-slim-buster as builder-arm64

FROM builder-${TARGETARCH}${TARGETVARIANT} as builder

WORKDIR /wheels
COPY --from=requirements /requirements_full.txt .

RUN pip wheel -w /wheels -r requirements_full.txt

############################################################################

FROM python:3.9-slim-buster as main-armv7
# arm/v7 debian buster does not have the same wheels as the rest, install libs

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
                    libpq5 \
 && rm -rf /var/lib/apt/lists/*

FROM python:3.9-slim-buster as main-amd64
FROM python:3.9-slim-buster as main-arm64

FROM main-${TARGETARCH}${TARGETVARIANT} as main

COPY --from=requirements /requirements_full.txt .
RUN --mount=type=bind,from=builder,src=/wheels,target=/wheels \
    pip install --no-index --find-links=/wheels -r /wheels/requirements_full.txt

WORKDIR /app/

ENV PYTHONUNBUFFERED=1

COPY surface surface
RUN touch /app/surface/local.env
WORKDIR /app/surface/
