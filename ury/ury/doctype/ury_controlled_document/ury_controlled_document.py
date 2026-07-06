# Copyright (c) 2026, Tridz Technologies Pvt. Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, now

PUBLISHED_STATUSES = {"Published", "Expired"}
MANAGER_ROLES = {"System Manager", "URY Manager"}


class URYControlledDocument(Document):
	def validate(self):
		self.set_default_dates()
		self.validate_content()
		self.validate_dates()
		self.validate_restaurant_branch()
		self.validate_unique_current_revision()
		self.update_expiry_flag()

	def before_submit(self):
		if self.status not in {"Approved", "Published"}:
			frappe.throw(_("Only Approved or Published documents can be submitted."))
		self.validate_content()

	def on_submit(self):
		self.publish_document()

	def on_update_after_submit(self):
		self.update_expiry_flag()

	def set_default_dates(self):
		if not self.effective_date and self.status in {"Approved", "Published"}:
			self.effective_date = getdate()
		if self.category and not self.next_review_date:
			review_period = frappe.db.get_value("URY Document Category", self.category, "default_review_period_days")
			if review_period and self.effective_date:
				self.next_review_date = add_days(self.effective_date, int(review_period))

	def validate_content(self):
		if self.status in PUBLISHED_STATUSES and not (self.file_attachment or self.external_url):
			frappe.throw(_("Published controlled documents require a file attachment or external URL."))

	def validate_dates(self):
		if self.effective_date and self.expiry_date and getdate(self.expiry_date) < getdate(self.effective_date):
			frappe.throw(_("Expiry Date cannot be before Effective Date."))
		if self.next_review_date and self.expiry_date and getdate(self.next_review_date) > getdate(self.expiry_date):
			frappe.throw(_("Next Review Date cannot be after Expiry Date."))

	def validate_restaurant_branch(self):
		if self.restaurant and self.branch:
			restaurant_branch = frappe.db.get_value("URY Restaurant", self.restaurant, "branch")
			if restaurant_branch and restaurant_branch != self.branch:
				frappe.throw(_("Selected Restaurant does not belong to the selected Branch."))

	def validate_unique_current_revision(self):
		current_count = 0
		for row in self.revisions:
			if row.is_current:
				current_count += 1
		if current_count > 1:
			frappe.throw(_("Only one revision can be marked as current."))

	def update_expiry_flag(self):
		self.is_expired = 1 if self.expiry_date and getdate(self.expiry_date) < getdate() else 0
		if self.is_expired and self.status == "Published":
			self.status = "Expired"

	def publish_document(self):
		if self.status != "Published":
			self.db_set("status", "Published", update_modified=False)
		if not self.published_on:
			self.db_set("published_on", now(), update_modified=False)
		self.ensure_revision()
		self.create_acknowledgements()

	def ensure_revision(self):
		if any(row.is_current for row in self.revisions):
			return
		revision_no = self.current_revision or "1"
		self.append(
			"revisions",
			{
				"revision_no": revision_no,
				"revision_date": getdate(),
				"change_summary": _("Initial published revision"),
				"changed_by": frappe.session.user,
				"approved_by": self.approved_by,
				"approval_date": getdate() if self.approved_by else None,
				"file_attachment": self.file_attachment,
				"is_current": 1,
			},
		)
		self.db_set("current_revision", revision_no, update_modified=False)
		self.save(ignore_permissions=True)

	def create_acknowledgements(self):
		if not self.requires_acknowledgement:
			return
		for row in self.distribution:
			if not row.requires_acknowledgement:
				continue
			users = get_distribution_users(row)
			for user in users:
				if frappe.db.exists(
					"URY Document Acknowledgement",
					{"controlled_document": self.name, "revision_no": self.current_revision, "user": user},
				):
					continue
				ack = frappe.new_doc("URY Document Acknowledgement")
				ack.controlled_document = self.name
				ack.revision_no = self.current_revision
				ack.user = user
				ack.role = row.role
				ack.branch = row.branch or self.branch
				ack.restaurant = row.restaurant or self.restaurant
				ack.insert(ignore_permissions=True)


@frappe.whitelist()
def create_new_revision(document, change_summary=None):
	doc = frappe.get_doc("URY Controlled Document", document)
	doc.check_permission("write")
	previous_revision = doc.current_revision
	for row in doc.revisions:
		row.is_current = 0
	try:
		next_revision = str(int(doc.current_revision or "0") + 1)
	except ValueError:
		next_revision = f"{doc.current_revision}.1"
	doc.current_revision = next_revision
	doc.status = "Revision Required"
	doc.append(
		"revisions",
		{
			"revision_no": next_revision,
			"revision_date": getdate(),
			"change_summary": change_summary or _("New revision created"),
			"changed_by": frappe.session.user,
			"file_attachment": doc.file_attachment,
			"previous_revision": previous_revision,
			"is_current": 1,
		},
	)
	doc.save()
	return doc.name


@frappe.whitelist()
def publish_document(document):
	doc = frappe.get_doc("URY Controlled Document", document)
	doc.check_permission("submit")
	doc.status = "Published"
	doc.published_on = now()
	doc.save()
	if doc.docstatus == 0:
		doc.submit()
	else:
		doc.publish_document()
	return doc.name


@frappe.whitelist()
def mark_superseded(document, superseded_by=None):
	doc = frappe.get_doc("URY Controlled Document", document)
	doc.check_permission("write")
	doc.status = "Superseded"
	doc.superseded_by = superseded_by
	doc.save(ignore_permissions=True)
	return doc.name


@frappe.whitelist()
def acknowledge_document(document, remarks=None):
	doc = frappe.get_doc("URY Controlled Document", document)
	doc.check_permission("read")
	if doc.status != "Published":
		frappe.throw(_("Only published documents can be acknowledged."))
	ack = frappe.get_doc(
		{
			"doctype": "URY Document Acknowledgement",
			"controlled_document": doc.name,
			"revision_no": doc.current_revision,
			"user": frappe.session.user,
			"branch": doc.branch,
			"restaurant": doc.restaurant,
			"remarks": remarks,
		}
	)
	ack.insert(ignore_permissions=True)
	return ack.name


def get_distribution_users(row):
	users = set()
	if row.user:
		users.add(row.user)
	if row.role:
		for user in frappe.get_all("Has Role", filters={"role": row.role, "parenttype": "User"}, pluck="parent"):
			if frappe.db.get_value("User", user, "enabled"):
				users.add(user)
	return users
