# syntax=docker/dockerfile:1
FROM frappe/build:version-16@sha256:ee3d5d7015782c086b3641c6a84b05e2ade7faa7be7a96eb67f795cb3fcb487f AS builder
ARG FRAPPE_REF=v16.52.0
ARG FRAPPE_COMMIT=4515014c87ece6cb20ee91d2cfb121c5cbd1ff4a
COPY apps/saeenaria_portal/constraints-runtime.txt /opt/runtime-constraints.txt
ENV UV_HTTP_TIMEOUT=60 UV_HTTP_RETRIES=3 \
    UV_CONSTRAINT=/opt/runtime-constraints.txt PIP_CONSTRAINT=/opt/runtime-constraints.txt \
    UV_CACHE_DIR=/home/frappe/.cache/uv
# Cache the framework separately so portal edits do not reinstall Frappe.
RUN --mount=type=cache,target=/home/frappe/.cache/uv,uid=1000,gid=1000 \
    bench init --verbose --frappe-branch=${FRAPPE_REF} --no-procfile --no-backups --skip-redis-config-generation /home/frappe/frappe-bench \
 && test "$(git -C /home/frappe/frappe-bench/apps/frappe rev-parse HEAD)" = "$FRAPPE_COMMIT"
COPY --chown=frappe:frappe apps/saeenaria_portal /home/frappe/frappe-bench/apps/saeenaria_portal
RUN cd /home/frappe/frappe-bench \
 && env/bin/pip install --no-cache-dir -e apps/saeenaria_portal \
 && printf 'frappe\nsaeenaria_portal\n' > sites/apps.txt \
 && bench build --app saeenaria_portal
FROM frappe/base:version-16@sha256:797ff4f07470b2fa797c131752e2a73bcbff90fca7f22e2fa4e40897ca936474
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench /home/frappe/frappe-bench
COPY --from=builder --chown=frappe:frappe /home/frappe/frappe-bench/sites/assets /opt/portal-assets
WORKDIR /home/frappe/frappe-bench
ENV PATH=/home/frappe/frappe-bench/env/bin:$PATH
USER frappe
CMD ["/home/frappe/frappe-bench/env/bin/gunicorn", "--chdir=/home/frappe/frappe-bench/sites", "--bind=0.0.0.0:8000", "--workers=2", "--threads=4", "--timeout=120", "frappe.app:application"]
