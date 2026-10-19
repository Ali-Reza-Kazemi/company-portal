#!/usr/bin/env bash
set -euo pipefail
if [ ! -f "sites/$SITE_NAME/site_config.json" ]; then
  bench new-site "$SITE_NAME" --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD" --mariadb-user-host-login-scope '%'
fi
bench --site "$SITE_NAME" install-app saeenaria_portal
bench --site "$SITE_NAME" execute saeenaria_portal.seed.run
bench --site "$SITE_NAME" enable-scheduler
