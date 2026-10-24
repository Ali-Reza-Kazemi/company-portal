"""The only purchasing-policy input store: native portal documents."""

import frappe


def read_inputs():
    from . import general_settings, incoming_orders, product_catalog

    if not product_catalog.active() or not general_settings.active():
        frappe.throw(
            "فهرست کالاها و تنظیمات خرید باید در پورتال راه‌اندازی شوند؛ منبع جایگزین خارجی استفاده نمی‌شود"
        )
    return {
        "ProductMapping": product_catalog.mapping_rows(),
        "GeneralSettings": general_settings.rows(),
        "IncomingOrders": incoming_orders.rows(),
        "metadata": [
            {
                "source": "portal-native-v2",
                "portal_settings_revision": frappe.db.get_single_value(
                    general_settings.DT, "revision"
                ),
                "portal_settings_at": frappe.db.get_single_value(general_settings.DT, "updated_at"),
                "portal_catalog_sync": frappe.db.get_single_value(
                    product_catalog.SETTINGS, "last_sync"
                ),
                "portal_incoming_at": frappe.db.get_value(
                    incoming_orders.DT, {}, "modified", order_by="modified desc"
                ),
            }
        ],
    }
