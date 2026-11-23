# Copyright (c) 2026
# For license information, please see license.txt

from collections import Counter, OrderedDict
from datetime import datetime, timedelta

import frappe
from frappe import _
from frappe.utils import flt, formatdate, get_datetime, get_first_day, get_last_day, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)

	columns = get_columns()
	data = get_data(filters)

	if not data:
		return columns, [], _("No late arrivals found for the selected filters."), None, []

	chart = get_trend_chart(data)
	report_summary = get_report_summary(data)

	return columns, data, None, chart, report_summary


def validate_filters(filters):
	# Haddii taariikh la waayo (tusaale JS-ka filter-yada ma shaqayn), bisha hadda ayaa la qaadanayaa
	if not filters.get("from_date"):
		filters.from_date = get_first_day(nowdate())
	if not filters.get("to_date"):
		filters.to_date = get_last_day(nowdate())
	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date"))


def get_columns():
	return [
		{"label": _("Employee ID"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 130},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 170},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 130},
		{"label": _("Date"), "fieldname": "attendance_date", "fieldtype": "Date", "width": 110},
		{"label": _("Shift Start"), "fieldname": "shift_start", "fieldtype": "Data", "width": 100},
		{"label": _("Check-in Time"), "fieldname": "checkin_time", "fieldtype": "Data", "width": 120},
		{"label": _("Late Minutes"), "fieldname": "late_minutes", "fieldtype": "Int", "width": 120},
		{"label": _("Late Hours"), "fieldname": "late_hours", "fieldtype": "Float", "precision": 2, "width": 110},
		{"label": _("Late Count"), "fieldname": "late_count", "fieldtype": "Int", "width": 110},
	]


def get_conditions(filters):
	conditions = ""
	if filters.get("company"):
		conditions += " AND att.company = %(company)s"
	if filters.get("employee"):
		conditions += " AND att.employee = %(employee)s"
	if filters.get("department"):
		conditions += " AND att.department = %(department)s"
	if filters.get("branch"):
		conditions += " AND emp.branch = %(branch)s"
	if filters.get("shift_type"):
		conditions += " AND COALESCE(att.shift, emp.default_shift) = %(shift_type)s"
	return conditions


def get_data(filters):
	conditions = get_conditions(filters)

	# Haddii shift la waayo, waxaa la isticmaalayaa filter-ka "Default Shift Start" (08:00)
	default_start = to_timedelta(filters.get("default_shift_start") or "08:00:00")

	rows = frappe.db.sql(
		f"""
		SELECT
			att.employee,
			att.employee_name,
			att.department,
			att.attendance_date,
			st.start_time AS shift_start_raw,
			COALESCE(
				att.in_time,
				(
					SELECT MIN(ec.time)
					FROM `tabEmployee Checkin` ec
					WHERE ec.employee = att.employee
						AND DATE(ec.time) = att.attendance_date
						AND IFNULL(ec.log_type, 'IN') IN ('IN', '')
				)
			) AS checkin
		FROM `tabAttendance` att
		INNER JOIN `tabEmployee` emp ON emp.name = att.employee
		LEFT JOIN `tabShift Type` st ON st.name = COALESCE(att.shift, emp.default_shift)
		WHERE
			att.docstatus != 2
			AND att.status IN ('Present', 'Half Day', 'Work From Home')
			AND att.attendance_date BETWEEN %(from_date)s AND %(to_date)s
			{conditions}
		ORDER BY att.attendance_date ASC, att.employee ASC
		""",
		filters,
		as_dict=True,
	)

	data = []
	running_count = Counter()
	for row in rows:
		if not row.checkin:
			continue

		checkin = get_datetime(row.checkin)
		start_delta = to_timedelta(row.shift_start_raw) if row.shift_start_raw is not None else default_start
		shift_start_dt = datetime.combine(getdate(row.attendance_date), datetime.min.time()) + start_delta

		late_minutes = int((checkin - shift_start_dt).total_seconds() // 60)
		if late_minutes <= 0:
			continue

		running_count[row.employee] += 1
		data.append(
			frappe._dict(
				employee=row.employee,
				employee_name=row.employee_name,
				department=row.department,
				attendance_date=row.attendance_date,
				shift_start=format_time(start_delta),
				checkin_time=checkin.strftime("%H:%M"),
				late_minutes=late_minutes,
				late_hours=flt(late_minutes / 60.0, 2),
				late_count=running_count[row.employee],
			)
		)

	return data


def to_timedelta(value):
	"""Time / timedelta / 'HH:MM[:SS]' -> timedelta."""
	if isinstance(value, timedelta):
		return value
	if hasattr(value, "hour"):
		return timedelta(hours=value.hour, minutes=value.minute, seconds=value.second)
	parts = [int(p) for p in str(value).split(":")] + [0, 0]
	return timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])


def format_time(value):
	"""timedelta -> 'HH:MM'."""
	if value is None:
		return ""
	total = int(to_timedelta(value).total_seconds())
	return f"{total // 3600:02d}:{(total % 3600) // 60:02d}"


def get_trend_chart(data):
	per_day = OrderedDict()
	for row in data:
		per_day.setdefault(row.attendance_date, set()).add(row.employee)

	labels = [formatdate(d, "dd MMM") for d in per_day]
	values = [len(emps) for emps in per_day.values()]

	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Late Employees"), "values": values}],
		},
		"type": "line",
		"colors": ["#1a73e8"],
		"lineOptions": {"regionFill": 1, "dotSize": 6},
		"valuesOverPoints": 1,
		"title": _("Late Arrival Trend"),
		"height": 280,
	}


def get_report_summary(data):
	employees = {row.employee for row in data}
	total_minutes = sum(row.late_minutes for row in data)
	avg_minutes = flt(total_minutes / len(employees), 2) if employees else 0

	dept_minutes = Counter()
	for row in data:
		dept_minutes[row.department or _("Not Set")] += row.late_minutes
	most_late_dept = dept_minutes.most_common(1)[0][0] if dept_minutes else "-"

	return [
		{"value": len(employees), "label": _("Total Employees Late"), "datatype": "Int", "indicator": "Red"},
		{"value": total_minutes, "label": _("Total Late Minutes"), "datatype": "Int", "indicator": "Blue"},
		{"value": most_late_dept, "label": _("Most Late Department"), "datatype": "Data", "indicator": "Green"},
		{"value": avg_minutes, "label": _("Average Late Minutes"), "datatype": "Float", "indicator": "Purple"},
	]