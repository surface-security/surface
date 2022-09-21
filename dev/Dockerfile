FROM --platform=$BUILDPLATFORM ghcr.io/surface-security/compile-requirements:4 as requirements
# merge all requirements.txt files together
# as we bind mount the whole context here, this stage will have cache invalidated on any context changes
# but the remaining stages that only use /requirements_full.txt will not

RUN --mount=type=bind,target=/tmpapp \
    python /run.py /tmpapp/surface/requirements.txt \
                   /tmpapp/surface/requirements_prod.txt \
                   /tmpapp/surface/requirements_psql.txt > /requirements_full.txt

FROM python:3.9-slim-buster as builder

RUN apt-get update \
 && apt-get install --no-install-recommends -y \
        libmariadbclient-dev \
        build-essential \
        libldap2-dev \
        libsasl2-dev \
        git \
        libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /wheels
COPY --from=requirements /requirements_full.txt .

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
