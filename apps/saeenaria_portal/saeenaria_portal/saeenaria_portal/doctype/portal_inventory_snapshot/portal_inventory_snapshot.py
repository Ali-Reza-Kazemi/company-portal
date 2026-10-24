import frappe
from frappe.model.document import Document


class PortalInventorySnapshot(Document):
    def validate(self):
        if not self.is_new() or not getattr(frappe.local, "inventory_capture_internal", False):
            frappe.throw("نسخه ثبت‌شده پایش موجودی تغییر نمی‌کند؛ نسخه تازه ثبت کنید")

    def on_trash(self):
        frappe.throw("سابقه پایش موجودی حذف نمی‌شود")
