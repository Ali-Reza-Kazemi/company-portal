#!/usr/bin/env bash
set -euo pipefail
cp -a /opt/portal-assets/. sites/assets/
printf 'frappe\nsaeenaria_portal\n' > sites/apps.txt
bench set-config -g db_host db
bench set-config -g redis_cache redis://redis-cache:6379
bench set-config -g redis_queue redis://redis-queue:6379
bench set-config -g redis_socketio redis://redis-queue:6379
bench set-config -gp socketio_port 9000
# Production source connections must use verified, full-session TLS.
bench set-config -gp purchase_order_require_tls True
