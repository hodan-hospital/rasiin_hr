import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

ENDED = "Ended"
ON_LEAVE = "On Leave"
UPCOMING = "Upcoming"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	rows = get_rows(filters)
	summary = get_summary(rows)

	data = rows
	if filters.get("end_status"):
		data = [row for row in rows if row["end_status"] == filters.end_status]

	for idx, row in enumerate(data, 1):
		row["idx"] = idx

	if data:
		data.append(get_total_row(data))

	return get_columns(), data, None, None, summary


def validate_filters(filters):
	if not filters.get("company"):
		frappe.throw(_("Please select Company"))
	if not filters.get("from_date") or not filters.get("to_date"):
		frappe.throw(_("Please select From Date and To Date"))
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns():
	return [
		{"label": _("#"), "fieldname": "idx", "fieldtype": "Int", "width": 60},
		{"label": _("Employee ID"), "fieldname": "employee_id", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 170},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 180},
		{"label": _("Leave Type"), "fieldname": "leave_type", "fieldtype": "Link", "options": "Leave Type", "width": 150},
		{"label": _("From Date"), "fieldname": "from_date", "fieldtype": "Date", "width": 120},
		{"label": _("To Date"), "fieldname": "to_date", "fieldtype": "Date", "width": 120},
		{"label": _("Leave Days"), "fieldname": "leave_days", "fieldtype": "Float", "precision": 1, "width": 110},
		{"label": _("End Status"), "fieldname": "end_status", "fieldtype": "Data", "width": 120},
	]


def get_rows(filters):
	conditions = [
		"la.docstatus = 1",
		"la.status = 'Approved'",
		"la.from_date <= %(to_date)s",
		"la.to_date >= %(from_date)s",
	]

	if filters.get("company"):
		conditions.append("la.company = %(company)s")
	if filters.get("branch"):
		conditions.append("emp.branch = %(branch)s")
	if filters.get("department"):
		conditions.append("la.department = %(department)s")
	if filters.get("leave_type"):
		conditions.append("la.leave_type = %(leave_type)s")
	if filters.get("employee"):
		conditions.append("la.employee = %(employee)s")

	rows = frappe.db.sql(
		f"""
		SELECT
			la.employee AS employee_id,
			la.employee_name,
			la.department,
			la.leave_type,
			la.from_date,
			la.to_date,
			la.total_leave_days AS leave_days
		FROM `tabLeave Application` la
		INNER JOIN `tabEmployee` emp ON emp.name = la.employee
		WHERE {" AND ".join(conditions)}
		ORDER BY la.employee, la.from_date
		""",
		filters,
		as_dict=True,
	)

	today = getdate(nowdate())
	for row in rows:
		row["leave_days"] = flt(row.leave_days, 1)

		if getdate(row.from_date) <= today <= getdate(row.to_date):
			row["end_status"] = ON_LEAVE
		elif getdate(row.to_date) < today:
			row["end_status"] = ENDED
		else:
			row["end_status"] = UPCOMING

	return rows


def get_summary(rows):
	ended = [row for row in rows if row["end_status"] == ENDED]
	on_leave = [row for row in rows if row["end_status"] == ON_LEAVE]
	employees = {row["employee_id"] for row in rows}
	total_days = sum(flt(row["leave_days"]) for row in rows)

	return [
		{"value": len(ended), "label": _("Total Ended Leaves"), "datatype": "Int", "indicator": "Blue"},
		{"value": len(on_leave), "label": _("On Leave Now"), "datatype": "Int", "indicator": "Orange"},
		{"value": flt(total_days, 1), "label": _("Total Leave Days"), "datatype": "Float", "indicator": "Purple"},
		{"value": len(employees), "label": _("Employees"), "datatype": "Int", "indicator": "Green"},
	]


def get_total_row(data):
	return {
		"employee_id": _("Total"),
		"leave_days": flt(sum(flt(row["leave_days"]) for row in data), 1),
		"end_status": len(data),
		"bold": 1,
	}