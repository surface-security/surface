#!/usr/bin/env bash


docker run -d --name dev-surface-mysql \
              -p33306:3306 \
              --health-cmd='mysqladmin ping --silent' --health-interval='5s' \
              -e MYSQL_INNODB_BUFFER_POOL_SIZE=512M \
              -e MYSQL_DATABASE=surface \
              -e MYSQL_ALLOW_EMPTY_PASSWORD=yes \
              mysql:8.0.30

echo "Waiting for MySQL to be ready..."
while ! docker exec dev-surface-mysql mysqladmin ping -h localhost --silent; do
    sleep 1
done

echo "Loading timezone info..."
docker exec dev-surface-mysql bash -c 'mysql_tzinfo_to_sql /usr/share/zoneinfo | mysql -u root mysql'

echo "MySQL container is ready!"