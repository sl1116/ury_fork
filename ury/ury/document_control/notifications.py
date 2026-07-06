import frappe
from frappe import _


def get_document_recipients(doc):
	recipients = set()
	for field in ("document_owner", "prepared_by", "reviewed_by", "approved_by"):
		if doc.get(field):
			recipients.add(doc.get(field))
	for user in frappe.get_all("Has Role", filters={"role": "URY Manager", "parenttype": "User"}, pluck="parent"):
		if frappe.db.get_value("User", user, "enabled"):
			recipients.add(user)
	return list(recipients)


def notify_expiry(doc, reminder_type):
	recipients = get_document_recipients(doc)
	if not recipients:
		return []
	subject = _("Controlled Document {0} is {1}").format(doc.document_code, reminder_type)
	message = _("Document {0} - {1} has expiry date {2}.").format(doc.document_code, doc.title, doc.expiry_date)
	frappe.sendmail(recipients=recipients, subject=subject, message=message, delayed=False)
	return recipients
