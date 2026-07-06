import frappe


def execute():
	create_workflow_states()
	create_workflow_actions()
	create_document_workflow()


def create_workflow_states():
	for state, style in {
		"Draft": "Primary",
		"Under Review": "Warning",
		"Pending Approval": "Warning",
		"Approved": "Info",
		"Published": "Success",
		"Revision Required": "Danger",
		"Expired": "Danger",
		"Superseded": "Inverse",
		"Archived": "Inverse",
		"Cancelled": "Danger",
	}.items():
		if not frappe.db.exists("Workflow State", state):
			doc = frappe.new_doc("Workflow State")
			doc.workflow_state_name = state
			doc.style = style
			doc.insert(ignore_permissions=True)


def create_workflow_actions():
	for action in [
		"Submit for Review",
		"Request Revision",
		"Submit for Approval",
		"Approve",
		"Publish",
		"Mark Superseded",
		"Archive",
		"Cancel",
	]:
		if not frappe.db.exists("Workflow Action Master", action):
			doc = frappe.new_doc("Workflow Action Master")
			doc.workflow_action_name = action
			doc.insert(ignore_permissions=True)


def create_document_workflow():
	name = "URY Document Control Workflow"
	if frappe.db.exists("Workflow", name):
		return

	workflow = frappe.new_doc("Workflow")
	workflow.workflow_name = name
	workflow.document_type = "URY Controlled Document"
	workflow.workflow_state_field = "status"
	workflow.is_active = 1
	workflow.send_email_alert = 0

	for state, doc_status, allow_edit in [
		("Draft", 0, "URY Manager"),
		("Under Review", 0, "URY Manager"),
		("Pending Approval", 0, "URY Manager"),
		("Approved", 0, "URY Manager"),
		("Published", 1, "URY Manager"),
		("Revision Required", 0, "URY Manager"),
		("Expired", 1, "URY Manager"),
		("Superseded", 1, "URY Manager"),
		("Archived", 1, "URY Manager"),
		("Cancelled", 2, "System Manager"),
	]:
		workflow.append("states", {"state": state, "doc_status": doc_status, "allow_edit": allow_edit})

	for state, action, next_state, allowed in [
		("Draft", "Submit for Review", "Under Review", "URY Manager"),
		("Under Review", "Request Revision", "Revision Required", "URY Manager"),
		("Under Review", "Submit for Approval", "Pending Approval", "URY Manager"),
		("Pending Approval", "Approve", "Approved", "URY Manager"),
		("Approved", "Publish", "Published", "URY Manager"),
		("Published", "Request Revision", "Revision Required", "URY Manager"),
		("Published", "Mark Superseded", "Superseded", "URY Manager"),
		("Published", "Archive", "Archived", "URY Manager"),
		("Draft", "Cancel", "Cancelled", "System Manager"),
		("Under Review", "Cancel", "Cancelled", "System Manager"),
		("Pending Approval", "Cancel", "Cancelled", "System Manager"),
	]:
		workflow.append(
			"transitions",
			{"state": state, "action": action, "next_state": next_state, "allowed": allowed},
		)

	workflow.insert(ignore_permissions=True)
