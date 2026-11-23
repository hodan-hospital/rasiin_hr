# Copyright (c) 2025, Hodan Hospital and contributors
# License: MIT

import frappe
from frappe import _
from frappe.utils import flt, getdate, today

# ---- Magacyada Leave Type (ku badal kuwa System-kaaga ku jira haddii ay kala duwan yihiin) ----
ANNUAL_LEAVE = "Annual Leave"   # ama "Privilege Leave"
SICK_LEAVE = "Sick Leave"
MATERNITY_LEAVE = "Maternity Leave"
MARRIAGE_LEAVE = "Mariage Leave"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	employees = get_employees(filters)
	if not employees:
		return get_columns(), [], None, None, get_summary([])

	emp_ids = [e.name for e in employees]
	allocations = get_allocations(emp_ids, filters)
	used = get_used_leaves(emp_ids, filters)
	on_leave_today = get_employees_on_leave_today(emp_ids)
	lwp_types = {d.name for d in frappe.get_all("Leave Type", filters={"is_lwp": 1}, fields=["name"])}

	data = []
	for emp in employees:
		alloc = allocations.get(emp.name, {})
		use = used.get(emp.name, {})

		annual_alloc = flt(alloc.get(ANNUAL_LEAVE))
		annual_used = flt(use.get(ANNUAL_LEAVE))
		sick_alloc = flt(alloc.get(SICK_LEAVE))
		sick_used = flt(use.get(SICK_LEAVE))
		maternity_alloc = flt(alloc.get(MATERNITY_LEAVE))
		maternity_used = flt(use.get(MATERNITY_LEAVE))
		marriage_alloc = flt(alloc.get(MARRIAGE_LEAVE))
		marriage_used = flt(use.get(MARRIAGE_LEAVE))
		unpaid = sum(flt(v) for lt, v in use.items() if lt in lwp_types)

		status = "On Leave" if emp.name in on_leave_today else "Active"
		if filters.get("status") not in (None, "", "All Statuses") and filters.status != status:
			continue

		data.append(
			{
				"employee": emp.name,
				"employee_name": emp.employee_name,
				"department": emp.department,
				"designation": emp.designation,
				"annual_allocated": annual_alloc,
				"annual_used": annual_used,
				"annual_balance": annual_alloc - annual_used,
				"sick_allocated": sick_alloc,
				"sick_used": sick_used,
				"sick_balance": sick_alloc - sick_used,
				"maternity_balance": maternity_alloc - maternity_used,
				"marriage_balance": marriage_alloc - marriage_used,
				"unpaid_leave": unpaid,
				"leave_status": status,
			}
		)

	return get_columns(), data, None, None, get_summary(data)


def validate_filters(filters):
	# Haddii taariikhdu maqan tahay, isticmaal sanadka hadda socda
	year = getdate(today()).year
	if not filters.get("from_date"):
		filters.from_date = f"{year}-01-01"
	if not filters.get("to_date"):
		filters.to_date = f"{year}-12-31"
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def get_employees(filters):
	conditions = {"status": "Active"}
	for field in ("company", "branch", "department"):
		if filters.get(field):
			conditions[field] = filters[field]
	if filters.get("employee"):
		conditions["name"] = filters.employee

	return frappe.get_all(
		"Employee",
		filters=conditions,
		fields=["name", "employee_name", "department", "designation"],
		order_by="name asc",
	)


def get_allocations(emp_ids, filters):
	conditions = {
		"docstatus": 1,
		"employee": ["in", emp_ids],
		"from_date": ["<=", filters.to_date],
		"to_date": [">=", filters.from_date],
	}
	if filters.get("leave_type"):
		conditions["leave_type"] = filters.leave_type

	result = {}
	for d in frappe.get_all(
		"Leave Allocation",
		filters=conditions,
		fields=["employee", "leave_type", "total_leaves_allocated"],
	):
		result.setdefault(d.employee, {}).setdefault(d.leave_type, 0)
		result[d.employee][d.leave_type] += flt(d.total_leaves_allocated)
	return result


def get_used_leaves(emp_ids, filters):
	conditions = {
		"docstatus": 1,
		"status": "Approved",
		"employee": ["in", emp_ids],
		"from_date": ["<=", filters.to_date],
		"to_date": [">=", filters.from_date],
	}
	if filters.get("leave_type"):
		conditions["leave_type"] = filters.leave_type

	result = {}
	for d in frappe.get_all(
		"Leave Application",
		filters=conditions,
		fields=["employee", "leave_type", "total_leave_days"],
	):
		result.setdefault(d.employee, {}).setdefault(d.leave_type, 0)
		result[d.employee][d.leave_type] += flt(d.total_leave_days)
	return result


def get_employees_on_leave_today(emp_ids):
	rows = frappe.get_all(
		"Leave Application",
		filters={
			"docstatus": 1,
			"status": "Approved",
			"employee": ["in", emp_ids],
			"from_date": ["<=", today()],
			"to_date": [">=", today()],
		},
		fields=["employee"],
	)
	return {r.employee for r in rows}


def get_columns():
	return [
		{"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 110},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 150},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 170},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 150},
		{"label": _("Annual Allocated"), "fieldname": "annual_allocated", "fieldtype": "Float", "precision": 1, "width": 100},
		{"label": _("Annual Used"), "fieldname": "annual_used", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Annual Balance"), "fieldname": "annual_balance", "fieldtype": "Float", "precision": 1, "width": 100},
		{"label": _("Sick Allocated"), "fieldname": "sick_allocated", "fieldtype": "Float", "precision": 1, "width": 100},
		{"label": _("Sick Used"), "fieldname": "sick_used", "fieldtype": "Float", "precision": 1, "width": 80},
		{"label": _("Sick Balance"), "fieldname": "sick_balance", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Maternity Balance"), "fieldname": "maternity_balance", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("Marriage Balance"), "fieldname": "marriage_balance", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("Unpaid Leave"), "fieldname": "unpaid_leave", "fieldtype": "Float", "precision": 1, "width": 90},
		{"label": _("Leave Status"), "fieldname": "leave_status", "fieldtype": "Data", "width": 110},
	]


def get_summary(data):
	return [
		{"value": len(data), "label": _("Total Employees"), "datatype": "Int", "indicator": "Blue"},
		{
			"value": sum(d["annual_balance"] for d in data),
			"label": _("Annual Leave Balance"),
			"datatype": "Float",
			"indicator": "Green",
			"precision": 1,
		},
		{
			"value": sum(d["sick_balance"] for d in data),
			"label": _("Sick Leave Balance"),
			"datatype": "Float",
			"indicator": "Red",
			"precision": 1,
		},
		{
			"value": sum(d["maternity_balance"] for d in data),
			"label": _("Maternity Leave Balance"),
			"datatype": "Float",
			"indicator": "Purple",
			"precision": 1,
		},
		{
			"value": sum(d["marriage_balance"] for d in data),
			"label": _("Marriage Leave Balance"),
			"datatype": "Float",
			"indicator": "Orange",
			"precision": 1,
		},
	]