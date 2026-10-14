#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/workspace
if [ ! -d portal-bench ]; then
  bench init --frappe-branch version-16 --skip-redis-config-generation portal-bench
fi
cd portal-bench
bench set-config -g db_host db
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
bench set-config -g socketio_port 9000
bench set-config -g developer_mode 1
if [ ! -f sites/portal.localhost/site_config.json ]; then
  bench new-site portal.localhost --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD" --mariadb-user-host-login-scope '%'
fi
bench use portal.localhost
bench --site portal.localhost set-config host_name http://portal.localhost:8085
