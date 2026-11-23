// Copyright (c) 2026
// For license information, please see license.txt

frappe.query_reports["Employee Late Arrive"] = {
	filters: [
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.month_end(),
		},
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "shift_type",
			label: __("Shift Type"),
			fieldtype: "Link",
			options: "Shift Type",
		},
		{
			fieldname: "default_shift_start",
			label: __("Default Shift Start"),
			fieldtype: "Time",
			default: "08:00:00",
			description: __("Used when the employee has no Shift Type"),
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "late_minutes" && data && data.late_minutes >= 30) {
			value = `<span style="color:#e02424;font-weight:600">${value}</span>`;
		}
		return value;
	},

	// Line chart-ka (trend) waxaa soo celiya Python; pie chart-ka department-ka halkan ayaa lagu sameeyaa
	after_datatable_render() {
		try {
			render_department_pie();
		} catch (e) {
			console.error("Employee Late Arrival pie chart error:", e);
		}
	},
};

function render_department_pie() {
	const qr = frappe.query_report;
	if (!qr || !qr.$chart) return;

	const rows = (qr.data || []).filter((r) => r && r.employee);

	// Trend chart + pie chart dhinac-dhinac
	let $row = qr.page.main.find(".late-charts-row");
	if (!$row.length) {
		$row = $(`<div class="late-charts-row" style="display:flex;gap:16px;align-items:stretch;"></div>`);
		$row.insertBefore(qr.$chart);
		qr.$chart.css({ flex: "1 1 64%", minWidth: 0 }).appendTo($row);
		$row.append(`
			<div class="late-dept-pie frappe-card" style="flex:1 1 36%;min-width:0;padding:12px 16px;margin-bottom:var(--margin-lg,16px);">
				<div style="font-weight:600;font-size:var(--text-md,14px);margin-bottom:4px;">${__("Late Arrival by Department")}</div>
				<div class="late-dept-pie-body"></div>
			</div>`);
	}

	const $pie = $row.find(".late-dept-pie");
	if (!rows.length) {
		$pie.hide();
		return;
	}
	$pie.show();

	const counts = {};
	rows.forEach((r) => {
		const dept = r.department || __("Not Set");
		counts[dept] = (counts[dept] || 0) + 1;
	});
	const total = rows.length;
	const labels = Object.keys(counts).map(
		(d) => `${d} (${Math.round((counts[d] / total) * 100)}%)`
	);

	const body = $pie.find(".late-dept-pie-body")[0];
	body.innerHTML = "";
	new frappe.Chart(body, {
		type: "pie",
		height: 260,
		data: {
			labels: labels,
			datasets: [{ values: Object.values(counts) }],
		},
		colors: ["#1a73e8", "#4cc25a", "#fb9d0c", "#9b4ff0", "#e02424", "#0ea5e9"],
	});
}