from frappe.model.document import Document

class PortalReviewDelegation(Document):
    def validate(self):
        from saeenaria_portal.reviews import delegation_validate
        delegation_validate(self)
