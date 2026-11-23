# Copyright (c) 2026, Rasiin Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate

# column in "Hr assigment TABLE" -> Leave Type
LEAVE_TYPES = {
	"annual_leave": "Annual Leave",
	"sick_leave": "Sick Leave",
	"marriage_leave": "Mariage Leave",
	"maternity_leave": "Maternity Leave",
}

MAX_ERRORS_SHOWN = 20
BACKGROUND_CANCEL_ABOVE = 300


class Hrassignment(Document):
	def validate(self):
		if self.from_date and self.to_date and getdate(self.from_date) >= getdate(self.to_date):
			frappe.throw(_("To Date must be after From Date"))

	def before_submit(self):
		if not self.from_date or not self.to_date:
			frappe.throw(_("From Date and To Date are required to create leave allocations"))
		if not self.hr:
			frappe.throw(_("Add at least one employee before submitting"))

	def on_submit(self):
		self.create_leave_allocations()

	def on_cancel(self):
		self.cancel_leave_allocations()

	def allocation_marker(self):
		"""Stored in Leave Allocation.description so the allocations made by
		this document can be found again on cancel."""
		return "Hr assignment: {0}".format(self.name)

	def create_leave_allocations(self):
		"""One submitted Leave Allocation per employee per leave type.

		An employee who already has a submitted allocation of that leave type
		overlapping the period is skipped. Any other problem stops the submit
		and nothing is created."""
		already_allocated = set(
			frappe.get_all(
				"Leave Allocation",
				filters={
					"docstatus": 1,
					"leave_type": ("in", list(LEAVE_TYPES.values())),
					"from_date": ("<=", self.to_date),
					"to_date": (">=", self.from_date),
				},
				fields=["employee", "leave_type"],
				as_list=True,
			)
		)

		created, skipped, errors = 0, 0, []

		for row in self.hr:
			if not row.employee:
				continue

			for fieldname, leave_type in LEAVE_TYPES.items():
				days = flt(row.get(fieldname))
				if days <= 0:
					continue

				if (row.employee, leave_type) in already_allocated:
					skipped += 1
					continue

				allocation = frappe.get_doc(
					{
						"doctype": "Leave Allocation",
						"employee": row.employee,
						"leave_type": leave_type,
						"from_date": self.from_date,
						"to_date": self.to_date,
						"new_leaves_allocated": days,
						"description": self.allocation_marker(),
					}
				)
				allocation.flags.ignore_permissions = True

				try:
					allocation.insert()
					allocation.submit()
				except frappe.ValidationError as e:
					frappe.clear_messages()
					errors.append(
						_("Row {0}: {1} ({2}), {3}: {4}").format(
							row.idx, row.employee_name or "", row.employee, leave_type, str(e)
						)
					)
					continue

				already_allocated.add((row.employee, leave_type))
				created += 1

		if errors:
			shown = errors[:MAX_ERRORS_SHOWN]
			if len(errors) > MAX_ERRORS_SHOWN:
				shown.append(_("... and {0} more").format(len(errors) - MAX_ERRORS_SHOWN))
			frappe.throw(
				"<br>".join(shown),
				title=_("Leave allocations could not be created; nothing was saved"),
			)

		message = _("{0} leave allocations created.").format(created)
		if skipped:
			message += " " + _("{0} skipped because the employee already has that leave type for this period.").format(skipped)
		frappe.msgprint(message, title=_("Leave Allocation"), indicator="green")

	def cancel_leave_allocations(self):
		names = frappe.get_all(
			"Leave Allocation",
			filters={"docstatus": 1, "description": self.allocation_marker()},
			pluck="name",
		)
		if not names:
			return

		if len(names) > BACKGROUND_CANCEL_ABOVE:
			# cancelling is slow (about 0.15s each), a big batch would time out the request
			frappe.enqueue(
				cancel_allocations,
				queue="long",
				timeout=3600,
				enqueue_after_commit=True,
				names=names,
				hr_assignment=self.name,
			)
			frappe.msgprint(
				_("{0} leave allocations are being cancelled in the background. Check Error Log if any remain.").format(len(names))
			)
		else:
			cancel_allocations(names)
			frappe.msgprint(_("{0} leave allocations cancelled.").format(len(names)))


def cancel_allocations(names, hr_assignment=None):
	try:
		for name in names:
			allocation = frappe.get_doc("Leave Allocation", name)
			if allocation.docstatus != 1:
				continue
			allocation.flags.ignore_permissions = True
			allocation.cancel()
	except Exception:
		if hr_assignment:
			# background job: undo the partial work and leave a trace
			frappe.db.rollback()
			frappe.log_error(title="Hr assignment {0}: cancelling leave allocations failed".format(hr_assignment))
		raise
