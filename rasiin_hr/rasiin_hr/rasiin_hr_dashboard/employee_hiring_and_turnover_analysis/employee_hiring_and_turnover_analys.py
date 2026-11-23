import re

import frappe
import requests
from frappe import _


POWER_BI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"
AZURE_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
POWER_BI_API_BASE = "https://api.powerbi.com/v1.0/myorg"


@frappe.whitelist()
def get_embed_config(report_url=None, report_id=None, workspace_id=None):
	"""Return the embed configuration needed by the Power BI JS client."""
	settings = _get_power_bi_settings()
	context = _resolve_report_context(
		report_url=report_url or settings.get("report_url"),
		report_id=report_id or settings.get("report_id"),
		workspace_id=workspace_id or settings.get("workspace_id"),
	)
	access_token = _get_azure_access_token(settings)
	report = _get_report_metadata(access_token, context)
	embed_token = _generate_embed_token(access_token, context)

	return {
		"report_id": context["report_id"],
		"workspace_id": context.get("workspace_id"),
		"report_name": report.get("name"),
		"report_url": context.get("report_url"),
		"embed_url": report.get("embedUrl"),
		"access_token": embed_token.get("token"),
		"token_expiration": embed_token.get("expiration"),
		"token_type": "Embed",
	}


def _get_power_bi_settings():
	doctype_settings = _get_power_bi_settings_from_doctype()
	settings = {
		"tenant_id": doctype_settings.get("tenant_id") or frappe.conf.get("power_bi_tenant_id"),
		"client_id": doctype_settings.get("client_id") or frappe.conf.get("power_bi_client_id"),
		"client_secret": doctype_settings.get("client_secret") or frappe.conf.get("power_bi_client_secret"),
		"workspace_id": doctype_settings.get("workspace_id") or frappe.conf.get("power_bi_workspace_id"),
		"report_id": doctype_settings.get("report_id") or frappe.conf.get("power_bi_report_id"),
		"report_url": doctype_settings.get("report_url") or frappe.conf.get("power_bi_report_url"),
	}

	missing = [key for key in ("tenant_id", "client_id", "client_secret") if not settings.get(key)]
	if missing:
		frappe.throw(
			_("Missing Power BI settings: {0}").format(", ".join(missing))
		)

	return settings


def _get_power_bi_settings_from_doctype():
	if not frappe.db.exists("DocType", "Powerbi Settings"):
		return {}

	doc = frappe.get_cached_doc("Powerbi Settings")
	return {
		"tenant_id": doc.tenant_id,
		"client_id": doc.client_id,
		"client_secret": doc.get_password("client_secret", raise_exception=False),
		"workspace_id": doc.workspace_id,
		"report_id": doc.report_id,
		"report_url": doc.report_url,
	}


def _resolve_report_context(report_url=None, report_id=None, workspace_id=None):
	parsed_report_id = None
	parsed_workspace_id = None

	if report_url:
		parsed_report_id = _extract_report_id(report_url)
		parsed_workspace_id = _extract_workspace_id(report_url)

	final_report_id = report_id or parsed_report_id
	final_workspace_id = workspace_id or parsed_workspace_id

	if not final_report_id:
		frappe.throw(
			_("Missing Power BI report id. Set it in Power BI Settings, site_config.json, or pass a valid report URL.")
		)

	# Service principal embedding needs a real workspace id; "me" cannot be used.
	if final_workspace_id == "me":
		if not workspace_id:
			frappe.throw(
				_(
					"Power BI embed token flow needs the real workspace id. Add workspace_id in Power BI Settings or power_bi_workspace_id in site_config.json instead of using groups/me."
				)
			)
		final_workspace_id = workspace_id

	return {
		"report_id": final_report_id,
		"workspace_id": final_workspace_id,
		"report_url": report_url,
	}


def _extract_report_id(report_url):
	match = re.search(r"/reports/([a-f0-9-]+)", report_url or "", re.IGNORECASE)
	return match.group(1) if match else None


def _extract_workspace_id(report_url):
	match = re.search(r"/groups/([^/]+)", report_url or "", re.IGNORECASE)
	return match.group(1) if match else None


def _get_azure_access_token(settings):
	response = requests.post(
		AZURE_TOKEN_URL.format(tenant_id=settings["tenant_id"]),
		data={
			"grant_type": "client_credentials",
			"client_id": settings["client_id"],
			"client_secret": settings["client_secret"],
			"scope": POWER_BI_SCOPE,
		},
		timeout=30,
	)
	data = _parse_response(response, "Azure AD token")
	token = data.get("access_token")

	if not token:
		frappe.throw(_("Azure AD token response did not include an access_token."))

	return token


def _get_report_metadata(access_token, context):
	response = requests.get(
		_get_report_endpoint(context),
		headers=_build_power_bi_headers(access_token),
		timeout=30,
	)
	data = _parse_response(response, "Power BI report metadata")

	if not data.get("embedUrl"):
		frappe.throw(_("Power BI report metadata did not include an embedUrl."))

	return data


def _generate_embed_token(access_token, context):
	response = requests.post(
		f"{_get_report_endpoint(context)}/GenerateToken",
		headers=_build_power_bi_headers(access_token),
		json={"accessLevel": "View", "allowSaveAs": False},
		timeout=30,
	)
	return _parse_response(response, "Power BI embed token")


def _get_report_endpoint(context):
	if context.get("workspace_id"):
		return (
			f"{POWER_BI_API_BASE}/groups/{context['workspace_id']}/reports/{context['report_id']}"
		)

	return f"{POWER_BI_API_BASE}/reports/{context['report_id']}"


def _build_power_bi_headers(access_token):
	return {
		"Authorization": f"Bearer {access_token}",
		"Content-Type": "application/json",
	}


def _parse_response(response, label):
	try:
		payload = response.json()
	except ValueError:
		payload = None

	if response.ok:
		return payload or {}

	message = (response.text or "").strip() or response.reason or f"HTTP {response.status_code}"
	if isinstance(payload, dict):
		error = payload.get("error")
		if isinstance(error, dict):
			message = error.get("message") or error.get("code") or message
		elif error:
			message = str(error)
		elif payload.get("message"):
			message = payload.get("message")

	hint = ""
	if label == "Power BI report metadata":
		if response.status_code == 401:
			hint = _(
				" Check the Azure app credentials and confirm the Power BI tenant allows service principals to use Power BI APIs."
			)
		elif response.status_code == 403:
			hint = _(
				" Check that the service principal or its security group has access to the workspace and report."
			)
		elif response.status_code == 404:
			hint = _(
				" Check that workspace_id and report_id are correct and that the report is in a shared workspace, not My Workspace."
			)

	frappe.throw(
		_("{0} request failed ({1}): {2}{3}").format(
			label,
			response.status_code,
			message,
			hint,
		)
	)


HR_DASHBOARD_ROLES = ("System Manager", "HR Manager", "HR User")
FINANCE_DASHBOARD_ROLES = ("System Manager", "Accounts Manager", "Accounts User")
PNL_CACHE_SECONDS = 6 * 60 * 60
PNL_JOB_LOCK_SECONDS = 20 * 60


def _validate_year(year):
	try:
		selected_year = int(year or frappe.utils.nowdate()[:4])
	except (TypeError, ValueError):
		frappe.throw(_("Select a valid calendar year."))

	if selected_year < 1900 or selected_year > 2200:
		frappe.throw(_("Select a valid calendar year."))
	return selected_year


@frappe.whitelist()
def get_employee_hiring_dashboard(year=None):
	"""Employee movement for the year and the salary of leavers versus new hires.

	Salary per employee = gross pay of the employee's latest submitted Salary Slip,
	falling back to the base of the latest submitted Salary Structure Assignment.
	"""
	frappe.only_for(HR_DASHBOARD_ROLES)
	selected_year = _validate_year(year)
	start_date = frappe.utils.getdate(f"{selected_year}-01-01")
	end_date = frappe.utils.getdate(f"{selected_year}-12-31")
	previous_start_date = frappe.utils.getdate(f"{selected_year - 1}-01-01")

	employees = frappe.get_all(
		"Employee",
		filters={"date_of_joining": ["<=", end_date]},
		fields=[
			"name", "employee_name", "designation", "department",
			"date_of_joining", "relieving_date", "status",
		],
		limit_page_length=0,
	)

	hired_by_month = [0] * 12
	left_by_month = [0] * 12
	previous_hires = 0
	previous_left = 0
	opening_headcount = 0
	new_employees = []
	left_employees = []

	for employee in employees:
		joining_date = frappe.utils.getdate(employee.date_of_joining) if employee.date_of_joining else None
		relieving_date = frappe.utils.getdate(employee.relieving_date) if employee.relieving_date else None
		if not joining_date:
			continue

		if start_date <= joining_date <= end_date:
			hired_by_month[joining_date.month - 1] += 1
			new_employees.append(_movement_row(employee, joining_date))
		elif previous_start_date <= joining_date < start_date:
			previous_hires += 1

		if relieving_date and start_date <= relieving_date <= end_date:
			left_by_month[relieving_date.month - 1] += 1
			left_employees.append(_movement_row(employee, relieving_date))
		elif relieving_date and previous_start_date <= relieving_date < start_date:
			previous_left += 1

		is_left_without_date = (employee.status or "").lower() == "left" and not relieving_date
		if joining_date < start_date and not is_left_without_date:
			if not relieving_date or relieving_date >= start_date:
				opening_headcount += 1

	salaries = _latest_employee_salaries(
		[row["employee"] for row in new_employees + left_employees]
	)
	for row in new_employees + left_employees:
		row["salary"] = salaries.get(row["employee"])

	new_employees.sort(key=lambda row: row["date"], reverse=True)
	left_employees.sort(key=lambda row: row["date"], reverse=True)

	monthly_salaries = [{"former": [], "new": []} for _ in range(12)]
	for cohort, rows in (("former", left_employees), ("new", new_employees)):
		for row in rows:
			if row["salary"] is not None:
				monthly_salaries[frappe.utils.getdate(row["date"]).month - 1][cohort].append(row["salary"])

	left_salaries = [row["salary"] for row in left_employees if row["salary"] is not None]
	new_salaries = [row["salary"] for row in new_employees if row["salary"] is not None]
	former_average = _average_dashboard_salary(left_salaries)
	new_average = _average_dashboard_salary(new_salaries)
	salary_difference = (
		round(new_average - former_average, 2)
		if former_average is not None and new_average is not None
		else None
	)
	salary_change_percent = (
		round((salary_difference / former_average) * 100, 1)
		if salary_difference is not None and former_average
		else None
	)
	left_payroll = round(sum(left_salaries), 2)
	new_payroll = round(sum(new_salaries), 2)

	hires = sum(hired_by_month)
	left = sum(left_by_month)
	turnover_base = max(opening_headcount + hires, left)
	turnover_rate = round((left / turnover_base) * 100, 1) if turnover_base else 0

	months = []
	for month_index in range(12):
		former_month_average = _average_dashboard_salary(monthly_salaries[month_index]["former"])
		new_month_average = _average_dashboard_salary(monthly_salaries[month_index]["new"])
		month_date = frappe.utils.getdate(f"{selected_year}-{month_index + 1:02d}-01")
		months.append(
			{
				"label": month_date.strftime("%b"),
				"full_label": month_date.strftime("%B"),
				"hires": hired_by_month[month_index],
				"left": left_by_month[month_index],
				"net_change": hired_by_month[month_index] - left_by_month[month_index],
				"former_salary": former_month_average,
				"new_salary": new_month_average,
				"salary_difference": (
					round(new_month_average - former_month_average, 2)
					if former_month_average is not None and new_month_average is not None
					else None
				),
			}
		)

	return {
		"year": selected_year,
		"currency": frappe.defaults.get_global_default("currency"),
		"hires": hires,
		"left": left,
		"net_change": hires - left,
		"former_average_salary": former_average,
		"new_average_salary": new_average,
		"salary_difference": salary_difference,
		"salary_change_percent": salary_change_percent,
		"left_payroll": left_payroll,
		"new_payroll": new_payroll,
		"payroll_difference": round(new_payroll - left_payroll, 2),
		"hiring_change_percent": _percentage_change(hires, previous_hires),
		"turnover_change_percent": _percentage_change(left, previous_left),
		"turnover_rate": turnover_rate,
		"turnover_base": turnover_base,
		"months": months,
		"new_employees": new_employees,
		"left_employees": left_employees,
		"headcount": _headcount_by_department(new_employees, left_employees),
	}


def _headcount_by_department(new_employees, left_employees):
	"""Current Active / Left employees per department plus the selected year's movement."""
	rows = {}

	def row(department):
		department = department or _("No Department")
		if department not in rows:
			rows[department] = {
				"department": department,
				"active": 0,
				"left_total": 0,
				"inactive": 0,
				"hired_year": 0,
				"left_year": 0,
			}
		return rows[department]

	counts = frappe.get_all(
		"Employee",
		fields=["department", "status", "count(name) as count"],
		group_by="department, status",
		limit_page_length=0,
	)
	for count in counts:
		status = (count.status or "").lower()
		target = row(count.department)
		if status == "active":
			target["active"] += count.count
		elif status == "left":
			target["left_total"] += count.count
		else:
			target["inactive"] += count.count

	for employee in new_employees:
		row(employee["department"])["hired_year"] += 1
	for employee in left_employees:
		row(employee["department"])["left_year"] += 1

	return sorted(rows.values(), key=lambda item: (-item["active"], item["department"]))


def _movement_row(employee, date):
	return {
		"employee": employee.name,
		"employee_name": employee.employee_name,
		"designation": employee.designation,
		"department": employee.department,
		"date": str(date),
		"salary": None,
	}


def _latest_employee_salaries(employee_names):
	if not employee_names:
		return {}

	salaries = {}
	slips = frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "employee": ["in", employee_names]},
		fields=["employee", "gross_pay"],
		order_by="end_date desc, modified desc",
		limit_page_length=0,
	)
	for slip in slips:
		if slip.employee not in salaries and slip.gross_pay:
			salaries[slip.employee] = round(float(slip.gross_pay), 2)

	missing = [name for name in employee_names if name not in salaries]
	if missing:
		assignments = frappe.get_all(
			"Salary Structure Assignment",
			filters={"docstatus": 1, "employee": ["in", missing]},
			fields=["employee", "base"],
			order_by="from_date desc, modified desc",
			limit_page_length=0,
		)
		for assignment in assignments:
			if assignment.employee not in salaries and assignment.base:
				salaries[assignment.employee] = round(float(assignment.base), 2)

	return salaries


@frappe.whitelist()
def get_staff_movement(from_date=None, to_date=None):
	"""Employees who left and employees who joined between two dates, with their monthly salary."""
	frappe.only_for(HR_DASHBOARD_ROLES)
	today = frappe.utils.getdate()
	from_date = frappe.utils.getdate(from_date or f"{today.year}-01-01")
	to_date = frappe.utils.getdate(to_date or f"{today.year}-12-31")
	if from_date > to_date:
		frappe.throw(_("From Date cannot be after To Date."))

	fields = [
		"name", "employee_name", "first_name", "middle_name", "last_name",
		"department", "designation", "branch", "employment_type", "status",
		"date_of_joining", "relieving_date", "cell_number", "reason_for_leaving",
	]
	meta = frappe.get_meta("Employee")
	fields = [field for field in fields if field == "name" or meta.has_field(field)]

	left = frappe.get_all(
		"Employee",
		filters={"relieving_date": ["between", [from_date, to_date]]},
		fields=fields,
		order_by="relieving_date desc",
		limit_page_length=0,
	)
	joined = frappe.get_all(
		"Employee",
		filters={"date_of_joining": ["between", [from_date, to_date]]},
		fields=fields,
		order_by="date_of_joining desc",
		limit_page_length=0,
	)
	salaries = _latest_salary_details([row.name for row in left + joined])

	def build(row):
		salary = salaries.get(row.name) or {}
		return {
			"employee": row.name,
			"employee_name": _full_name(row),
			"department": row.get("department"),
			"designation": row.get("designation"),
			"branch": row.get("branch"),
			"employment_type": row.get("employment_type"),
			"status": row.get("status"),
			"date_of_joining": str(row.date_of_joining) if row.date_of_joining else None,
			"relieving_date": str(row.relieving_date) if row.relieving_date else None,
			"months_served": _months_between(row.date_of_joining, row.relieving_date or today),
			"reason_for_leaving": row.get("reason_for_leaving"),
			"salary": salary.get("salary"),
			"salary_source": salary.get("source"),
			"salary_period": salary.get("period"),
		}

	left_rows = [build(row) for row in left]
	new_rows = [build(row) for row in joined]

	def summary(rows):
		values = [row["salary"] for row in rows if row["salary"] is not None]
		return {
			"count": len(rows),
			"with_salary": len(values),
			"total_salary": round(sum(values), 2),
			"average_salary": _average_dashboard_salary(values),
		}

	left_summary = summary(left_rows)
	new_summary = summary(new_rows)
	return {
		"from_date": str(from_date),
		"to_date": str(to_date),
		"currency": frappe.defaults.get_global_default("currency"),
		"left": left_rows,
		"new": new_rows,
		"left_summary": left_summary,
		"new_summary": new_summary,
		"salary_difference": round(new_summary["total_salary"] - left_summary["total_salary"], 2),
	}


def _full_name(row):
	parts = [row.get("first_name"), row.get("middle_name"), row.get("last_name")]
	name = " ".join(part.strip() for part in parts if part and part.strip())
	name = name or (row.get("employee_name") or "")
	return " ".join(name.split())


def _months_between(start, end):
	if not start or not end:
		return None
	start = frappe.utils.getdate(start)
	end = frappe.utils.getdate(end)
	return max((end.year - start.year) * 12 + end.month - start.month, 0)


def _latest_salary_details(employee_names):
	"""Latest submitted Salary Slip gross pay per employee, else latest Salary Structure Assignment base."""
	if not employee_names:
		return {}

	details = {}
	slips = frappe.get_all(
		"Salary Slip",
		filters={"docstatus": 1, "employee": ["in", employee_names]},
		fields=["employee", "gross_pay", "start_date", "end_date", "pay_period_start"],
		order_by="end_date desc, modified desc",
		limit_page_length=0,
	)
	for slip in slips:
		if slip.employee not in details and slip.gross_pay:
			details[slip.employee] = {
				"salary": round(float(slip.gross_pay), 2),
				"source": "Salary Slip",
				"period": frappe.utils.getdate(slip.pay_period_start or slip.start_date).strftime("%b %Y"),
			}

	missing = [name for name in employee_names if name not in details]
	if missing:
		assignments = frappe.get_all(
			"Salary Structure Assignment",
			filters={"docstatus": 1, "employee": ["in", missing]},
			fields=["employee", "base", "from_date"],
			order_by="from_date desc, modified desc",
			limit_page_length=0,
		)
		for assignment in assignments:
			if assignment.employee not in details and assignment.base:
				details[assignment.employee] = {
					"salary": round(float(assignment.base), 2),
					"source": "Salary Structure",
					"period": frappe.utils.getdate(assignment.from_date).strftime("%b %Y"),
				}

	return details


@frappe.whitelist()
def get_hospital_profit_and_loss(year=None, company=None, refresh=0):
	"""Return cached income/expense figures, or queue their calculation.

	The GL Entry table is large, so the aggregate runs in a background job and
	the browser polls until it is ready.
	"""
	frappe.only_for(FINANCE_DASHBOARD_ROLES)
	selected_year = _validate_year(year)
	company = company or frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
		"Global Defaults", "default_company"
	)
	if not company or not frappe.db.exists("Company", company):
		frappe.throw(_("Select a valid company."))

	cache = frappe.cache()
	key = _pnl_cache_key(company, selected_year)
	lock_key = f"{key}:running"
	if frappe.utils.cint(refresh):
		cache.delete_value(key)
	else:
		cached = cache.get_value(key, expires=True)
		if cached:
			return {"status": "ready", "data": cached, "companies": _companies()}

	if not cache.get_value(lock_key, expires=True):
		cache.set_value(lock_key, 1, expires_in_sec=PNL_JOB_LOCK_SECONDS)
		frappe.enqueue(
			"rasiin_hr.rasiin_hr.page.hrm_dashboard.hrm_dashboard.build_hospital_profit_and_loss",
			queue="long",
			timeout=PNL_JOB_LOCK_SECONDS,
			company=company,
			year=selected_year,
		)

	return {"status": "pending", "company": company, "companies": _companies()}


def build_hospital_profit_and_loss(company, year):
	key = _pnl_cache_key(company, year)
	try:
		data = _compute_profit_and_loss(company, int(year))
		frappe.cache().set_value(key, data, expires_in_sec=PNL_CACHE_SECONDS)
	finally:
		frappe.cache().delete_value(f"{key}:running")


def _compute_profit_and_loss(company, year):
	start_date = f"{year}-01-01"
	end_date = f"{year}-12-31"
	accounts = {
		row.name: row
		for row in frappe.get_all(
			"Account",
			filters={"company": company, "root_type": ["in", ["Income", "Expense"]]},
			fields=["name", "account_name", "root_type"],
			limit_page_length=0,
		)
	}

	frappe.db.sql("SET SESSION sql_big_selects = 1")
	rows = frappe.db.sql(
		"""
		SELECT account, MONTH(posting_date) AS month,
			SUM(debit) AS debit, SUM(credit) AS credit
		FROM `tabGL Entry` FORCE INDEX (posting_date)
		WHERE posting_date BETWEEN %(start_date)s AND %(end_date)s
			AND company = %(company)s
			AND is_cancelled = 0
		GROUP BY account, MONTH(posting_date)
		""",
		{"start_date": start_date, "end_date": end_date, "company": company},
		as_dict=True,
	)

	income = [0.0] * 12
	expense = [0.0] * 12
	expense_by_account = {}
	income_by_account = {}
	for row in rows:
		account = accounts.get(row.account)
		if not account:
			continue
		month_index = int(row.month) - 1
		if account.root_type == "Income":
			amount = float(row.credit or 0) - float(row.debit or 0)
			income[month_index] += amount
			income_by_account[account.account_name] = income_by_account.get(account.account_name, 0) + amount
		else:
			amount = float(row.debit or 0) - float(row.credit or 0)
			expense[month_index] += amount
			expense_by_account[account.account_name] = expense_by_account.get(account.account_name, 0) + amount

	payroll_rows = frappe.db.sql(
		"""
		SELECT MONTH(COALESCE(pay_period_start, start_date)) AS month, SUM(gross_pay) AS gross
		FROM `tabSalary Slip`
		WHERE docstatus = 1 AND company = %(company)s
			AND COALESCE(pay_period_start, start_date) BETWEEN %(start_date)s AND %(end_date)s
		GROUP BY MONTH(COALESCE(pay_period_start, start_date))
		""",
		{"start_date": start_date, "end_date": end_date, "company": company},
		as_dict=True,
	)
	payroll = [0.0] * 12
	for row in payroll_rows:
		payroll[int(row.month) - 1] = float(row.gross or 0)

	months = []
	for month_index in range(12):
		month_date = frappe.utils.getdate(f"{year}-{month_index + 1:02d}-01")
		net = income[month_index] - expense[month_index]
		months.append(
			{
				"label": month_date.strftime("%b"),
				"full_label": month_date.strftime("%B"),
				"income": round(income[month_index], 2),
				"expense": round(expense[month_index], 2),
				"net": round(net, 2),
				"payroll": round(payroll[month_index], 2),
				"has_activity": bool(income[month_index] or expense[month_index]),
			}
		)

	total_income = round(sum(income), 2)
	total_expense = round(sum(expense), 2)
	net_profit = round(total_income - total_expense, 2)
	total_payroll = round(sum(payroll), 2)

	def top(mapping):
		items = sorted(mapping.items(), key=lambda item: item[1], reverse=True)[:8]
		return [{"account": name, "amount": round(amount, 2)} for name, amount in items if amount]

	return {
		"year": year,
		"company": company,
		"currency": frappe.get_cached_value("Company", company, "default_currency"),
		"total_income": total_income,
		"total_expense": total_expense,
		"net_profit": net_profit,
		"profit_margin": round((net_profit / total_income) * 100, 1) if total_income else None,
		"total_payroll": total_payroll,
		"payroll_share": round((total_payroll / total_expense) * 100, 1) if total_expense else None,
		"profit_months": sum(1 for month in months if month["has_activity"] and month["net"] > 0),
		"loss_months": sum(1 for month in months if month["has_activity"] and month["net"] < 0),
		"months": months,
		"top_expenses": top(expense_by_account),
		"top_income": top(income_by_account),
		"generated_at": frappe.utils.now(),
	}


def _pnl_cache_key(company, year):
	return f"rasiin_hr:hospital_pnl:{frappe.scrub(company)}:{year}"


def _companies():
	return frappe.get_all("Company", pluck="name", order_by="name")


@frappe.whitelist()
def get_employee_hiring_dashboard_chart(
	chart_name=None,
	filters=None,
	refresh=None,
	time_interval=None,
	timespan=None,
	from_date=None,
	to_date=None,
	heatmap_year=None,
):
	data = _get_dashboard_chart_data(filters)
	if chart_name == "Monthly Hiring vs Employee Turnover":
		datasets = [
			{"name": _("New Hires"), "values": [month["hires"] for month in data["months"]]},
			{"name": _("Employees Left"), "values": [month["left"] for month in data["months"]]},
		]
	elif chart_name == "Monthly Salary Comparison":
		datasets = [
			{
				"name": _("Former Staff Salary"),
				"values": [month["former_salary"] or 0 for month in data["months"]],
			},
			{
				"name": _("New Staff Salary"),
				"values": [month["new_salary"] or 0 for month in data["months"]],
			},
		]
	else:
		frappe.throw(_("Unknown Employee Hiring Dashboard chart: {0}").format(chart_name))

	return {
		"labels": [month["label"] for month in data["months"]],
		"datasets": datasets,
	}


def _get_dashboard_chart_data(filters):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	year = filters.get("year") if isinstance(filters, dict) else None
	return get_employee_hiring_dashboard(year=year)


def _average_dashboard_salary(values):
	return round(sum(values) / len(values), 2) if values else None


def _percentage_change(current, previous):
	if not previous:
		return None
	return round(((current - previous) / previous) * 100, 1)
