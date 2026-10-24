from frappe.model.document import Document


class PortalIncomingOrder(Document):
    def before_insert(self):
        from saeenaria_portal.purchase_reports.incoming_orders import ensure_order_key
        ensure_order_key(self)

    def validate(self):
        from saeenaria_portal.purchase_reports.incoming_orders import validate_document
        validate_document(self)
