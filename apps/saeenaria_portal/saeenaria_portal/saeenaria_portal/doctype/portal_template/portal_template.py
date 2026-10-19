import frappe
from frappe.model.document import Document
from saeenaria_portal.permissions import can_assign, can_domain

class PortalTemplate(Document):
    def validate(self):
        words=(self.description or "").split()
        self.description_preview=(" ".join(words[:12])+("…" if len(words)>12 else ""))[:140]
        self.responsible_name=frappe.db.get_value("User",self.responsible,"full_name") if self.responsible else ""
        if self.frequency == "Weekly" and self.weekday not in range(7):
            frappe.throw("روز هفته معتبر را انتخاب کنید")

        if self.responsible:
            if not frappe.db.get_value("User", self.responsible, "enabled"):
                frappe.throw("مسئول باید کاربر فعال باشد")
            if self.responsible != frappe.session.user and not can_assign(frappe.session.user,self.domain):
                frappe.throw("واگذاری به دیگران فقط برای مدیر واحد مجاز است",frappe.PermissionError)
            if not can_domain(self.responsible,self.domain,write=True):
                if not self.allow_external_responsible or not can_assign(frappe.session.user,self.domain):
                    frappe.throw("مسئول را از حوزه انتخاب‌شده انتخاب کنید یا نمایش همه کاربران را فعال کنید")
                if frappe.db.get_value("User",self.responsible,"user_type") != "System User":
                    frappe.throw("مسئول باید حساب فعال سامانه داشته باشد")
