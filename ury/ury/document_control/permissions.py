import frappe

MANAGER_ROLES = {"System Manager", "URY Manager"}
OPERATIONAL_ROLES = {"URY Captain", "URY Cashier"}


def user_is_manager(user=None):
	user = user or frappe.session.user
	return bool(MANAGER_ROLES.intersection(set(frappe.get_roles(user))))


def get_user_permission_values(doctype, user=None):
	user = user or frappe.session.user
	return frappe.get_all(
		"User Permission",
		filters={"user": user, "allow": doctype},
		pluck="for_value",
	)


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or user_is_manager(user):
		return ""

	conditions = ["`tabURY Controlled Document`.`status` = 'Published'"]
	branches = get_user_permission_values("Branch", user)
	restaurants = get_user_permission_values("URY Restaurant", user)

	visibility_parts = ["`tabURY Controlled Document`.`applies_to_all_branches` = 1"]
	if branches:
		escaped = ", ".join(frappe.db.escape(v) for v in branches)
		visibility_parts.append(f"`tabURY Controlled Document`.`branch` in ({escaped})")
	if restaurants:
		escaped = ", ".join(frappe.db.escape(v) for v in restaurants)
		visibility_parts.append(f"`tabURY Controlled Document`.`restaurant` in ({escaped})")

	conditions.append("(" + " or ".join(visibility_parts) + ")")
	return " and ".join(conditions)


def get_ack_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator" or user_is_manager(user):
		return ""
	return f"`tabURY Document Acknowledgement`.`user` = {frappe.db.escape(user)}"


def has_permission(doc, user=None, permission_type=None):
	user = user or frappe.session.user
	if user == "Administrator" or user_is_manager(user):
		return True
	if permission_type not in {None, "read", "print", "email"}:
		return False
	if doc.status != "Published":
		return False
	if doc.applies_to_all_branches:
		return True
	branches = set(get_user_permission_values("Branch", user))
	restaurants = set(get_user_permission_values("URY Restaurant", user))
	return bool((doc.branch and doc.branch in branches) or (doc.restaurant and doc.restaurant in restaurants))
