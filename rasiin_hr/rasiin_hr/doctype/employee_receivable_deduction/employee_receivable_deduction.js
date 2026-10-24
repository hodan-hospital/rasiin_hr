function update_employee_details(frm) {
    
    frappe.call({
        method: "rasiin_hr.rasiin_hr.doctype.employee_receivable_deduction.employee_receivable_deduction.get_employees_with_balances",
        args: {
            employee: frm.doc.employee || null,
            department: frm.doc.department || null,
            account: frm.doc.receivable_account 
        },
        callback: function(response) {
            if (response.message) {
                frm.clear_table("employee_receivable_details");

                let total_amount = 0;
                let total_payment = 0;

                response.message.forEach(emp => {
                    let child = frm.add_child("employee_receivable_details");
                    child.employee = emp.employee;
                    child.employee_name = emp.employee_name;
                    child.department = emp.department;
                    child.salary = emp.salary;
                    child.deduction = emp.deduction;
                    child.amount = emp.amount;
                    child.payment = flt(emp.amount);
                    child.balance = flt(emp.amount) - child.payment;

                    total_amount += flt(emp.amount);
                    total_payment += child.payment;
                    
                });

                frm.doc.total_due_amount = total_amount;
                frm.doc.total_deduction = total_payment;

                frm.refresh_field("employee_receivable_details");
                frm.refresh_field("total_due_amount");
                frm.refresh_field("total_deduction");

                // frappe.msgprint("Employee details loaded.");
            }
        }
    });
}

frappe.ui.form.on('Employee Receivable Deduction', {
        before_save(frm) {
     
        let total_amount = 0;
        let total_payment = 0;

        frm.doc.employee_receivable_details.forEach(row => {
            total_amount += flt(row.amount);
            total_payment += flt(row.payment);
        });

        frm.set_value('total_due_amount', total_amount);
        frm.set_value('total_deduction', total_payment);

        frm.refresh_field('total_due_amount');
        frm.refresh_field('total_deduction');
    },
    refresh(frm) {
        frm.set_query('receivable_account', function(doc) {
			return {
				filters: {
					"account_type": "Payable",
                    "company": frm.doc.company
				}
			};
		});
        frm.set_query('employee', function(doc) {
			return {
				filters: {
                    "status": "Active"
				}
			};
		});
        frm.set_query('department', function(doc) {
			return {
				filters: {
                    "company": frm.doc.company
				}
			};
		});
        frm.set_query('component', function(doc) {
			return {
				filters: {
					"type": "Deduction",
				}
			};
		});
        if (frm.is_new()) {
            update_employee_details(frm);
        }
    },
	department: update_employee_details,
	receivable_account: update_employee_details,
    employee: update_employee_details

});


frappe.ui.form.on('Employee Receivable Details', {
	 payment(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.balance = row.amount - row.payment;

        // Update totals when any payment changes
        let total_amount = 0;
        let total_payment = 0;

        frm.doc.employee_receivable_details.forEach(child => {
            total_amount += child.amount || 0;
            total_payment += child.payment || 0;
        });

        frm.doc.total_due_amount  = total_amount;
        frm.doc.total_deduction  = total_payment;

         frm.refresh_field("employee_receivable_details");
        frm.refresh_field("total_due_amount");
        frm.refresh_field("total_deduction");
    }
})
