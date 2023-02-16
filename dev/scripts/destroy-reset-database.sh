#!/usr/bin/env bash

DATABASE="${1:-surface}"

. $(dirname $0)/_common.sh

docker exec ${CONTAINER} mysql -e "drop database ${DATABASE};"
docker exec ${CONTAINER} mysql -e "create database ${DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;"