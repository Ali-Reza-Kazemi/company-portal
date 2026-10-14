#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/workspace/portal-bench
if [ ! -e apps/saein_portal ]; then ln -s /workspace/apps/saein_portal apps/saein_portal; fi
./env/bin/pip install --quiet -e apps/saein_portal
if ! grep -qx saein_portal sites/apps.txt; then printf '\nsaein_portal\n' >> sites/apps.txt; fi
bench --site portal.localhost install-app saein_portal
bench build --app saein_portal
bench --site portal.localhost clear-cache
# Redis is provided by Compose, not by bench start.
sed -i '/^redis_/d' Procfile
