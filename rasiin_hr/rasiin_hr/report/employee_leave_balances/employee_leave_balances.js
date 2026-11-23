// Copyright (c) 2025, Hodan Hospital and contributors
// License: MIT
// Employee Leave Balance Report - UI sida sawirka (header, filters, summary cards, table, total row)

const LR_TITLE = "Employee Leave Balance Report";
const LR_SUBTITLE = "";

// ---------- Icons (SVG) ----------
const LR_SVG = (inner) =>
	`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" width="26" height="26">${inner}</svg>`;

const LR_ICONS = {
	users: LR_SVG(
		`<circle cx="9" cy="8" r="3.2"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.5 0 4 1.8 4 4.5"/>`
	),
	calendar: LR_SVG(
		`<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M8 3v4M16 3v4M9 15l2 2 4-4"/>`
	),
	heart: LR_SVG(`<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>`),
	umbrella: LR_SVG(`<path d="M3 12a9 9 0 0 1 18 0z"/><path d="M12 12v6a2 2 0 0 1-4 0"/>`),
	user: LR_SVG(`<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>`),
};

// Icon-ka title-ka (document)
const LR_TITLE_ICON =
	"url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%232563eb' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><path d='M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z'/><path d='M14 3v5h5M9 13h6M9 17h6M9 9h2'/></svg>\")";

// ---------- CSS ----------
const LR_CSS = `
.leave-report { background: #f5f7fb; }

/* ===== Header ===== */
.leave-report .page-head .title-area {
	display: grid !important;
	grid-template-columns: 52px auto;
	column-gap: 16px;
	align-items: center;
}
.leave-report .page-head .title-area::before {
	content: "";
	grid-row: 1 / 3;
	width: 52px; height: 52px;
	border-radius: 12px;
	background: #e3eeff ${"${ICON}"} center / 26px 26px no-repeat;
}
.leave-report .page-head .title-area .title-text {
	grid-column: 2;
	font-size: 26px !important;
	font-weight: 700 !important;
	color: #0f1f3d !important;
	line-height: 1.2;
	max-width: none !important;
}
.leave-report .page-head .title-area .lr-subtitle {
	grid-column: 2;
	font-size: 14px;
	color: #5b6679;
	margin-top: 2px;
}
.leave-report .page-head .title-area > *:not(.title-text):not(.lr-subtitle) { display: none !important; }

.leave-report .page-head .btn-primary,
.leave-report .page-head .primary-action {
	background: #1a73e8 !important;
	border-color: #1a73e8 !important;
	border-radius: 8px !important;
	font-weight: 600;
	padding: 8px 18px;
}
.leave-report .page-head .btn-default {
	background: #fff !important;
	border: 1px solid #dfe5ee !important;
	border-radius: 8px !important;
	font-weight: 500;
	padding: 8px 16px;
}

/* ===== Filter card ===== */
.leave-report .page-form,
.leave-report .page-form.flex {
	display: block !important;
	background: #fff !important;
	border: 1px solid #e6ebf3 !important;
	border-radius: 14px !important;
	padding: 20px 24px !important;
	margin: 12px 0 16px !important;
	box-shadow: 0 1px 3px rgba(16, 24, 40, .05) !important;
}
.leave-report .standard-filter-section {
	display: grid !important;
	grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
	gap: 16px 24px !important;
	width: 100% !important;
}
.leave-report .standard-filter-section .frappe-control {
	width: 100% !important; max-width: none !important; min-width: 0 !important; margin: 0 !important;
}
.leave-report .standard-filter-section .form-group { margin-bottom: 0 !important; }
.leave-report .standard-filter-section .clearfix { display: block !important; height: auto !important; margin-bottom: 6px !important; }
.leave-report .standard-filter-section .control-label {
	display: block !important; font-size: 13px !important; font-weight: 500 !important; color: #1f2a44 !important;
}
.leave-report .standard-filter-section .form-control,
.leave-report .standard-filter-section input.input-with-feedback,
.leave-report .standard-filter-section select.form-control {
	height: 38px !important; background-color: #fff !important;
	border: 1px solid #dfe5ee !important; border-radius: 8px !important;
	font-size: 13px !important; color: #1f2a44 !important; box-shadow: none !important;
}
.leave-report .standard-filter-section .form-control:focus { border-color: #1a73e8 !important; }
.leave-report .standard-filter-section .form-control::placeholder { color: #8a94a6 !important; }

/* ===== Summary cards ===== */
.leave-report .report-summary { display: none !important; }
.lr-cards {
	display: grid;
	grid-template-columns: repeat(5, minmax(0, 1fr));
	gap: 16px;
	margin: 0 0 16px;
}
.lr-card {
	display: flex; align-items: center; gap: 16px;
	background: #fff; border: 1px solid #e6ebf3; border-radius: 14px;
	padding: 18px 20px;
	box-shadow: 0 1px 3px rgba(16, 24, 40, .05);
}
.lr-card .lr-ico {
	flex: 0 0 52px; width: 52px; height: 52px; border-radius: 12px;
	display: flex; align-items: center; justify-content: center;
}
.lr-card .lr-label { font-size: 13px; color: #1f2a44; font-weight: 500; line-height: 1.3; }
.lr-card .lr-value { font-size: 24px; font-weight: 700; color: #0f1f3d; line-height: 1.3; }
.lr-blue   .lr-ico { background: #e3eeff; color: #2563eb; }
.lr-green  .lr-ico { background: #dcfce7; color: #16a34a; }
.lr-red    .lr-ico { background: #fee2e2; color: #ef4444; }
.lr-purple .lr-ico { background: #ede9fe; color: #7c3aed; }
.lr-orange .lr-ico { background: #fef3c7; color: #f59e0b; }

/* ===== Table ===== */
.leave-report .datatable {
	background: #fff;
	border: 1px solid #e6ebf3 !important;
	border-radius: 12px;
	overflow: hidden;
}
.leave-report .dt-header .dt-cell {
	background: #f6f8fc !important;
	border-color: #e6ebf3 !important;
}
.leave-report .dt-header .dt-cell__content {
	font-weight: 600 !important; color: #1f2a44 !important; font-size: 13px;
}
.leave-report .dt-body .dt-cell { border-color: #eef1f6 !important; }
.leave-report .dt-body .dt-cell__content { font-size: 13px; color: #1f2a44; }
.leave-report .dt-row-totalRow .dt-cell,
.leave-report .dt-footer .dt-cell {
	background: #eaf0fb !important;
	font-weight: 700 !important;
}
.leave-report .dt-row-totalRow .dt-cell__content { font-weight: 700 !important; color: #0f1f3d !important; }

@media (max-width: 1199px) { .lr-cards { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 991px) {
	.leave-report .standard-filter-section { grid-template-columns: repeat(2, minmax(0, 1fr)) !important; }
	.lr-cards { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 575px) {
	.leave-report .standard-filter-section { grid-template-columns: 1fr !important; }
	.lr-cards { grid-template-columns: 1fr; }
}
`.replace("${ICON}", LR_TITLE_ICON);

// ---------- Helpers ----------
function lr_fmt(v) {
	return (Number(v) || 0).toLocaleString("en-US", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function lr_click_menu(report, text) {
	const $a = $(report.page.wrapper)
		.find(".menu-btn-group .dropdown-menu a, .menu-btn-group .dropdown-menu .dropdown-item")
		.filter(function () {
			return $(this).text().trim().toLowerCase().indexOf(text.toLowerCase()) === 0;
		})
		.first();
	if ($a.length) $a[0].click();
}

function lr_apply_style(report) {
	if (!document.getElementById("leave-report-css")) {
		$("<style id='leave-report-css'>").text(LR_CSS).appendTo("head");
	}
	// $(report.page.wrapper).addClass("leave-report");
	$(".page-container[data-page-route*='Employee Leave Balance']").addClass("leave-report");

	// Subtitle
	const $title = $(report.page.wrapper).find(".page-head .title-area").first();
	if ($title.length && !$title.find(".lr-subtitle").length) {
		$title.append(`<div class="lr-subtitle">${__(LR_SUBTITLE)}</div>`);
	}

	// Placeholders sida sawirka
	const placeholders = {
		branch: __("All Branches"),
		department: __("All Departments"),
		employee: __("Select Employee"),
		leave_type: __("All Leave Types"),
	};
	Object.keys(placeholders).forEach((name) => {
		const f = report.get_filter(name);
		if (f && f.$input) f.$input.attr("placeholder", placeholders[name]);
	});
}

function lr_add_buttons(report) {
	if (report.__lr_buttons) return;
	report.__lr_buttons = true;

	if (report.page.set_secondary_action) {
		report.page.set_secondary_action(__("Export"), () => lr_click_menu(report, "Export"), "es-line-download");
	}
	if (report.page.btn_secondary && !$(report.page.wrapper).find(".lr-print").length) {
		$(`<button class="btn btn-default btn-sm lr-print">${__("Print")}</button>`)
			.insertAfter(report.page.btn_secondary)
			.on("click", () => lr_click_menu(report, "Print"));
	}
}

function lr_render_cards(report) {
	const rows = (report.data || []).filter(
		(d) => d && d.employee && d.employee !== "Total" && d.employee !== __("Total")
	);
	const sum = (k) => rows.reduce((a, d) => a + (Number(d[k]) || 0), 0);

	const cards = [
		{ cls: "lr-blue", icon: "users", label: __("Total Employees"), value: rows.length },
		{ cls: "lr-green", icon: "calendar", label: __("Annual Leave Balance"), value: lr_fmt(sum("annual_balance")) + " days" },
		{ cls: "lr-red", icon: "heart", label: __("Sick Leave Balance"), value: lr_fmt(sum("sick_balance")) + " days" },
		{ cls: "lr-purple", icon: "umbrella", label: __("Maternity Leave Balance"), value: lr_fmt(sum("maternity_balance")) + " days" },
		{ cls: "lr-orange", icon: "user", label: __("Marriage Leave Balance"), value: lr_fmt(sum("marriage_balance")) + " days" },
	];

	const html = `<div class="lr-cards">${cards
		.map(
			(c) => `<div class="lr-card ${c.cls}">
				<div class="lr-ico">${LR_ICONS[c.icon]}</div>
				<div><div class="lr-label">${c.label}</div><div class="lr-value">${c.value}</div></div>
			</div>`
		)
		.join("")}</div>`;

	let $wrap = $(report.page.wrapper).find(".lr-cards-wrap");
	if (!$wrap.length) {
		$wrap = $('<div class="lr-cards-wrap"></div>');
		if (report.$summary && report.$summary.length) {
			report.$summary.before($wrap);
		} else {
			$(report.page.main).find(".report-wrapper").first().before($wrap);
		}
	}
	$wrap.html(html);
}

// ---------- Report ----------
const LR_REPORT_DEF = {
	onload: function (report) {
		// lr_apply_style(report);
		// lr_add_buttons(report);
		// setTimeout(() => lr_apply_style(report), 300);
		// setTimeout(() => lr_apply_style(report), 1000);
	},

	after_datatable_render: function () {
		const report = frappe.query_report;
		lr_apply_style(report);
		lr_render_cards(report);
	},

	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{ fieldname: "branch", label: __("Branch"), fieldtype: "Link", options: "Branch" },
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
			get_query: function () {
				return { filters: { company: frappe.query_report.get_filter_value("company") } };
			},
		},
		{ fieldname: "employee", label: __("Employee"), fieldtype: "Link", options: "Employee" },
		{ fieldname: "leave_type", label: __("Leave Type"), fieldtype: "Link", options: "Leave Type" },
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: moment().startOf("year").format("YYYY-MM-DD"),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: moment().endOf("year").format("YYYY-MM-DD"),
			reqd: 1,
		},
		{
			fieldname: "status",
			label: __("Status"),
			fieldtype: "Select",
			options: "All Statuses\nActive\nOn Leave",
			default: "All Statuses",
		},
	],

	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "leave_status" && data && data.leave_status) {
			const on_leave = data.leave_status === "On Leave";
			const bg = on_leave ? "#dbeafe" : "#dcfce7";
			const color = on_leave ? "#1d4ed8" : "#15803d";
			value = `<span style="background:${bg};color:${color};padding:2px 14px;border-radius:12px;font-weight:500;display:inline-block;">${data.leave_status}</span>`;
		}
		return value;
	},
};

// Ku diiwaangeli labada magac si JS-ku u shaqeeyo wixii magac ah ee report-ku leeyahay
["Employee Leave Balances", "Employee Leave Balance Report"].forEach((name) => {
	frappe.query_reports[name] = LR_REPORT_DEF;
});