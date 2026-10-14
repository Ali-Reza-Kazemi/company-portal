# syntax=docker/dockerfile:1
FROM frappe/build:version-16 AS builder
ARG FRAPPE_REF=v16.52.0
COPY --chown=frappe:frappe apps/saein_portal /opt/saein_portal
RUN bench init --frappe-branch=${FRAPPE_REF} --no-procfile --no-backups --skip-redis-config-generation /home/frappe/frappe-bench \
 && cp -a /opt/saein_portal /home/frappe/frappe-bench/apps/saein_portal \
 && cd /home/frappe/frappe-bench \
 && env/bin/pip install --no-cache-dir -e apps/saein_portal \
 && printf 'frappe\nsaein_portal\n' > sites/apps.txt \
 && bench build --app saein_portal
FROM frappe/base:version-16
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench/sites/assets /opt/portal-assets
WORKDIR /home/frappe/frappe-bench
ENV PATH=/home/frappe/frappe-bench/env/bin:$PATH
USER frappe
CMD ["/home/frappe/frappe-bench/env/bin/gunicorn", "--chdir=/home/frappe/frappe-bench/sites", "--bind=0.0.0.0:8000", "--workers=2", "--threads=4", "--timeout=120", "frappe.app:application"]
