frappe.provide("frappe.dashboards.chart_sources");

const get_year_filter = () => ({
	fieldname: "year",
	label: __("Year"),
	fieldtype: "Int",
	default: Number(frappe.datetime.get_today().slice(0, 4)),
	reqd: 1,
});

frappe.dashboards.chart_sources["Employee Hiring and Turnover Analysis"] = {
	method: "rasiin_hr.rasiin_hr.page.hrm_dashboard.hrm_dashboard.get_employee_hiring_dashboard_chart",
	filters: [get_year_filter()],
};
