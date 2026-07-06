import frappe
from frappe.model.document import Document
from frappe.utils import now


class URYDocumentAcknowledgement(Document):
	def validate(self):
		if not self.acknowledged_on:
			self.acknowledged_on = now()
		if not self.user:
			self.user = frappe.session.user
