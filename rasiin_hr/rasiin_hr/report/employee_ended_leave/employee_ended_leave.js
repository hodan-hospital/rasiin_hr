function ended_leave_svg(paths) {
	return `<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${paths}</svg>`;
}

const ENDED_LEAVE_ICONS = {
	users: ended_leave_svg(
		'<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M16 14.2c2.6.3 5 2.3 5 5.8"/>'
	),
	calendar: ended_leave_svg('<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>'),
	umbrella: ended_leave_svg('<path d="M23 12a11.05 11.05 0 0 0-22 0zM12 12v7a3 3 0 0 1-6 0"/>'),
	user: ended_leave_svg('<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/>'),
};

const ENDED_LEAVE_CARD_STYLE = {
	"Total Ended Leaves": { icon: ENDED_LEAVE_ICONS.users, color: "blue", suffix: "" },
	"On Leave Now": { icon: ENDED_LEAVE_ICONS.umbrella, color: "orange", suffix: "" },
	"Total Leave Days": { icon: ENDED_LEAVE_ICONS.calendar, color: "purple", suffix: " days" },
	"Employees": { icon: ENDED_LEAVE_ICONS.user, color: "green", suffix: "" },
};

function ensure_ended_leave_styles() {
	if (document.getElementById("ended-leave-card-styles")) return;

	const css = `
		.ended-leave-cards {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
			gap: 12px;
			margin: 12px 0;
		}
		.ended-leave-card {
			display: flex;
			align-items: center;
			gap: 12px;
			padding: 16px;
			border-radius: 10px;
			background: var(--card-bg);
			border: 1px solid var(--border-color);
		}
		.ended-leave-icon {
			width: 44px;
			height: 44px;
			border-radius: 10px;
			display: flex;
			align-items: center;
			justify-content: center;
			flex-shrink: 0;
		}
		.ended-leave-icon.blue { background: #e7f0ff; color: #1d6fe8; }
		.ended-leave-icon.green { background: #e6f7ec; color: #1f9d55; }
		.ended-leave-icon.purple { background: #efe9ff; color: #7c3aed; }
		.ended-leave-icon.orange { background: #fff3e0; color: #f08c00; }
		.ended-leave-label {
			font-size: 12px;
			color: var(--text-muted);
		}
		.ended-leave-value {
			font-size: 20px;
			font-weight: 600;
			color: var(--text-color);
		}
	`;

	$("<style>", { id: "ended-leave-card-styles", text: css }).appendTo("head");
}

function render_ended_leave_cards(report, summary) {
	const $container = report.page.main.find(".ended-leave-cards");

	const html = (summary || [])
		.map((item) => {
			const style = ENDED_LEAVE_CARD_STYLE[item.label] || {
				icon: ENDED_LEAVE_ICONS.calendar,
				color: "blue",
				suffix: "",
			};
			const fieldtype = item.datatype === "Float" ? "Float" : "Int";
			const value = frappe.format(item.value, { fieldtype: fieldtype, precision: 1 });

			return `
				<div class="ended-leave-card">
					<div class="ended-leave-icon ${style.color}">${style.icon}</div>
					<div>
						<div class="ended-leave-label">${frappe.utils.escape_html(item.label)}</div>
						<div class="ended-leave-value">${value}${style.suffix}</div>
					</div>
				</div>`;
		})
		.join("");

	$container.html(html);
}

frappe.query_reports["Employee Ended Leave"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			reqd: 1,
			default: frappe.defaults.get_user_default("Company"),
		},
		{
			fieldname: "branch",
			label: __("Branch"),
			fieldtype: "Link",
			options: "Branch",
		},
		{
			fieldname: "department",
			label: __("Department"),
			fieldtype: "Link",
			options: "Department",
		},
		{
			fieldname: "employee",
			label: __("Employee"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "leave_type",
			label: __("Leave Type"),
			fieldtype: "Link",
			options: "Leave Type",
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.year_start(),
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			reqd: 1,
			default: frappe.datetime.year_end(),
		},
		{
			fieldname: "end_status",
			label: __("End Status"),
			fieldtype: "Select",
			options: "\nEnded\nOn Leave\nUpcoming",
		},
	],

	onload(report) {
		ensure_ended_leave_styles();

		if (!report.page.main.find(".ended-leave-cards").length) {
			report.page.main.prepend('<div class="ended-leave-cards"></div>');
		}
	},

	refresh(report) {
		const filters = report.get_values();
		if (!filters || !filters.company || !filters.from_date || !filters.to_date) return;

		frappe.call({
			method: "frappe.desk.query_report.run",
			args: {
				report_name: "Employee Ended Leave",
				filters: filters,
				ignore_prepared_report: 1,
			},
			callback(r) {
				render_ended_leave_cards(report, (r.message && r.message.report_summary) || []);
			},
		});
	},

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (column.fieldname === "end_status" && data && data.end_status) {
			const colors = { Ended: "green", "On Leave": "blue", Upcoming: "orange" };
			const color = colors[data.end_status] || "gray";
			value = `<span class="indicator-pill ${color}">${value}</span>`;
		}

		return value;
	},
};