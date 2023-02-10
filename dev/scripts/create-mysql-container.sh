#!/usr/bin/env bash


docker run -d --name dev-surface-mysql \
              -p3306:3306 \
              -e MYSQL_INNODB_BUFFER_POOL_SIZE=512M \
              -e MYSQL_DATABASE=surface \
              mysql-dev:8.0.30-18
# Hack to wait a bit for MySQL - better if we do it with a check in the container, TODO later
sleep 15
docker exec surface-mysql-dev bash -c 'mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root mysql'
