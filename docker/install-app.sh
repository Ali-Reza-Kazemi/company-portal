#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/workspace/portal-bench
if [ ! -e apps/saeenaria_portal ]; then ln -s /workspace/apps/saeenaria_portal apps/saeenaria_portal; fi
./env/bin/pip install --quiet -e apps/saeenaria_portal
if ! grep -qx saeenaria_portal sites/apps.txt; then printf '\nsaeenaria_portal\n' >> sites/apps.txt; fi
bench --site portal.localhost install-app saeenaria_portal
bench build --app saeenaria_portal
bench --site portal.localhost clear-cache
# Redis is provided by Compose, not by bench start.
sed -i '/^redis_/d' Procfile
