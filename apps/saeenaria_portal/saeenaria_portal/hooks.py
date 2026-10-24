app_name = "saeenaria_portal"
app_title = "پورتال صائین آریا"
app_publisher = "Saeenaria Arya"
app_description = "Internal performance portal"
app_email = "admin@example.invalid"
app_license = "MIT"
after_install = "saeenaria_portal.install.after_install"
permission_query_conditions = {
    "Portal Action": "saeenaria_portal.permissions.action_query",
    "Portal Domain": "saeenaria_portal.permissions.domain_query",
}
has_permission = {
    "Portal Action": "saeenaria_portal.permissions.action_permission",
    "Portal Domain": "saeenaria_portal.permissions.domain_permission",
}
doc_events = {"Portal Action": {"validate": "saeenaria_portal.validation.validate_action"}}

SCOPED = ["Portal Metric", "Portal Metric Value", "Portal Report", "Portal Decision", "Portal Template", "Portal Record"]
for _dt in SCOPED:
    _slug = _dt.lower().replace(" ", "_")
    permission_query_conditions[_dt] = f"saeenaria_portal.permissions.{_slug}_query"
    has_permission[_dt] = "saeenaria_portal.permissions.scoped_permission"
    doc_events[_dt] = {"validate": "saeenaria_portal.rules.validate"}
scheduler_events = {"daily": ["saeenaria_portal.holidays.auto_sync", "saeenaria_portal.schedule.generate_today"]}
scheduler_events["hourly"] = ["saeenaria_portal.purchase_reports.service.auto_refresh"]
scheduler_events["daily"].append("saeenaria_portal.purchase_reports.workflow.enqueue_daily")
has_permission["Portal Inventory Snapshot"] = "saeenaria_portal.purchase_reports.workflow.snapshot_permission"
permission_query_conditions["Portal Inventory Snapshot"] = "saeenaria_portal.purchase_reports.workflow.snapshot_query"

app_include_css = ["/assets/saeenaria_portal/css/typography.css"]
web_include_css = ["/assets/saeenaria_portal/css/typography.css"]


app_include_js = ["/assets/saeenaria_portal/js/calendar.js", "/assets/saeenaria_portal/js/desk-calendar.js?v=4"]
app_include_css.append("/assets/saeenaria_portal/css/calendar.css?v=3")

after_migrate = ["saeenaria_portal.install.ensure_people_roles", "saeenaria_portal.install.refresh_template_labels", "saeenaria_portal.user_names.configure_user_titles"]

app_include_css.append("/assets/saeenaria_portal/css/branding.css?v=1")
web_include_css.append("/assets/saeenaria_portal/css/branding.css?v=1")

app_logo_url = "/assets/saeenaria_portal/images/saeenaria-logo.webp"
web_include_css.append("/assets/saeenaria_portal/css/login-brand.css?v=2")
web_include_js = ["/assets/saeenaria_portal/js/login-brand.js?v=3"]

app_include_js.append("/assets/saeenaria_portal/js/desk-persian.js?v=4")

app_include_js.append("/assets/saeenaria_portal/js/environments.js?v=1")
web_include_js.append("/assets/saeenaria_portal/js/environments.js?v=1")

# Independent review state, invalidated whenever the source activity changes.
for _dt in ("Portal Action", "Portal Record", "Portal Metric Value", "Portal Report"):
    doc_events[_dt]["on_update"] = "saeenaria_portal.reviews.sync"
doc_events["Portal Staff Request"] = {"validate":"saeenaria_portal.staff_requests.validate_request"}
doc_events["Portal Activity Review"] = {"validate":"saeenaria_portal.reviews.review_validate"}
has_permission["Portal Staff Request"] = "saeenaria_portal.staff_requests.request_permission"
permission_query_conditions["Portal Staff Request"] = "saeenaria_portal.staff_requests.request_query"

after_migrate.append("saeenaria_portal.staff_requests.migrate_legacy")

# Read-only Sepidar item synchronization; enrichment remains portal-owned.
scheduler_events.setdefault("hourly", []).append("saeenaria_portal.purchase_reports.product_catalog.auto_sync")

# Native defaults never fall back to an external workbook store.
after_migrate.append("saeenaria_portal.purchase_reports.general_settings.initialize")
