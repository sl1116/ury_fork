import frappe
from frappe.utils import date_diff, getdate, now

from ury.ury.document_control.notifications import notify_expiry

REMINDER_DAYS = {
	60: "60 Days",
	30: "30 Days",
	15: "15 Days",
	7: "7 Days",
	0: "Due Today",
}


def send_document_expiry_reminders():
	today = getdate()
	documents = frappe.get_all(
		"URY Controlled Document",
		filters={"status": ["in", ["Published", "Approved"]], "expiry_date": ["is", "set"]},
		fields=["name", "expiry_date"],
	)
	for item in documents:
		days_left = date_diff(item.expiry_date, today)
		reminder_type = REMINDER_DAYS.get(days_left)
		if days_left < 0:
			reminder_type = "Overdue"
		if not reminder_type:
			continue
		if reminder_already_logged(item.name, item.expiry_date, reminder_type):
			continue
		doc = frappe.get_doc("URY Controlled Document", item.name)
		try:
			recipients = notify_expiry(doc, reminder_type)
			create_expiry_log(doc, reminder_type, recipients, "Sent")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Document Control Expiry Reminder")
			create_expiry_log(doc, reminder_type, [], "Failed")


def mark_expired_documents():
	today = getdate()
	for name in frappe.get_all(
		"URY Controlled Document",
		filters={"status": ["in", ["Published", "Approved"]], "expiry_date": ["<", today]},
		pluck="name",
	):
		doc = frappe.get_doc("URY Controlled Document", name)
		doc.db_set("is_expired", 1, update_modified=False)
		doc.db_set("status", "Expired", update_modified=True)
		if not reminder_already_logged(name, doc.expiry_date, "Expired"):
			create_expiry_log(doc, "Expired", [], "Sent")


def reminder_already_logged(document, expiry_date, reminder_type):
	return frappe.db.exists(
		"URY Document Expiry Log",
		{"controlled_document": document, "expiry_date": expiry_date, "reminder_type": reminder_type},
	)


def create_expiry_log(doc, reminder_type, recipients, status):
	log = frappe.new_doc("URY Document Expiry Log")
	log.controlled_document = doc.name
	log.expiry_date = doc.expiry_date
	log.reminder_type = reminder_type
	log.sent_to = "\n".join(recipients or [])
	log.sent_on = now()
	log.status = status
	log.message = f"{reminder_type} reminder for {doc.document_code}"
	log.insert(ignore_permissions=True)
