app_name = "saein_portal"
app_title = "پورتال صائین آریا"
app_publisher = "Saein Arya"
app_description = "Internal performance portal"
app_email = "admin@example.invalid"
app_license = "MIT"
after_install = "saein_portal.install.after_install"
permission_query_conditions = {
    "Portal Action": "saein_portal.permissions.action_query",
    "Portal Domain": "saein_portal.permissions.domain_query",
}
has_permission = {
    "Portal Action": "saein_portal.permissions.action_permission",
    "Portal Domain": "saein_portal.permissions.domain_permission",
}
doc_events = {"Portal Action": {"validate": "saein_portal.validation.validate_action"}}

SCOPED = ["Portal Metric", "Portal Metric Value", "Portal Report", "Portal Decision", "Portal Template", "Portal Record"]
for _dt in SCOPED:
    _slug = _dt.lower().replace(" ", "_")
    permission_query_conditions[_dt] = f"saein_portal.permissions.{_slug}_query"
    has_permission[_dt] = "saein_portal.permissions.scoped_permission"
    doc_events[_dt] = {"validate": "saein_portal.rules.validate"}
scheduler_events = {"daily": ["saein_portal.schedule.generate_today"]}
