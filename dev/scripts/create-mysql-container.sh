#!/usr/bin/env bash


docker run -d --name dev-surface-mysql \
              -p33306:3306 \
              --health-cmd='mysqladmin ping --silent' --health-interval='5s' \
              -e MYSQL_INNODB_BUFFER_POOL_SIZE=512M \
              -e MYSQL_DATABASE=surface \
              -e MYSQL_ALLOW_EMPTY_PASSWORD=yes \
              mysql:8.0.30
# Hack to wait a bit for MySQL - better if we do it with a check in the container, TODO later
docker exec dev-surface-mysql bash -c 'mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root mysql'
