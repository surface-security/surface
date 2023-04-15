#!/usr/bin/env bash


docker run -d --name dev-surface-psql \
              --health-cmd='pg_isready -U $POSTGRES_USER' --health-interval='5s' \
              -p 35432:5432 \
              -e POSTGRES_PASSWORD=surfdbpassword \
              -e POSTGRES_USER=surface \
              postgres:15.2-alpine
