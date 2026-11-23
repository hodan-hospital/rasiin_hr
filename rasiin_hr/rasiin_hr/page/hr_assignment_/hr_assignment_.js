
const DEFAULT_LEAVES = {
    annual_leave: 26,
    sick_leave: 12,
    marriage_leave: 7,
    maternity_leave: 26
};

frappe.ui.form.on('Hr assignment', {

    onload(frm) {
        if (frm.is_new() && !(frm.doc.hr || []).length) {
            load_active_employees(frm);
        }
    },

    refresh(frm) {
        // submitted / cancelled documents are read only
        if (frm.doc.docstatus !== 0) return;

        fill_missing_leaves(frm, true);

        frm.add_custom_button(__('Get Active Employees'), () => {
            load_active_employees(frm);
        });
    },

    validate(frm) {
        fill_missing_leaves(frm, false);
    },

    // Ticking the box drops employees who already have a leave allocation;
    // unticking it brings the rest of the active employees back.
    only_non_allocated_employee(frm) {
        load_active_employees(frm);
    },

    from_date(frm) {
        if (frm.doc.only_non_allocated_employee) {
            load_active_employees(frm);
        }
    },

    to_date(frm) {
        if (frm.doc.only_non_allocated_employee) {
            load_active_employees(frm);
        }
    },

    hr_add(frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        Object.assign(row, DEFAULT_LEAVES);

        frm.refresh_field('hr');
    }
});

function fill_missing_leaves(frm, mark_dirty) {
    let changed = false;

    (frm.doc.hr || []).forEach(row => {
        Object.entries(DEFAULT_LEAVES).forEach(([field, value]) => {
            if (!row[field]) {
                row[field] = value;
                changed = true;
            }
        });
    });

    if (changed) {
        frm.refresh_field('hr');

        if (mark_dirty) {
            frm.dirty();
        }
    }
}

// Employees holding a submitted Leave Allocation that overlaps the
// From Date - To Date of this document (any allocation at all when the
// dates are empty). Empty set when the checkbox is off.
function get_allocated_employees(frm) {
    if (!frm.doc.only_non_allocated_employee) {
        return Promise.resolve(new Set());
    }

    const filters = { docstatus: 1 };

    if (frm.doc.to_date) {
        filters.from_date = ['<=', frm.doc.to_date];
    }

    if (frm.doc.from_date) {
        filters.to_date = ['>=', frm.doc.from_date];
    }

    return frappe.db.get_list('Leave Allocation', {
        filters: filters,
        fields: ['employee'],
        limit: 0
    }).then(rows => new Set(rows.map(row => row.employee)));
}

function load_active_employees(frm) {

    Promise.all([
        frappe.db.get_list('Employee', {
            filters: {
                status: 'Active'
            },
            fields: ['name', 'employee_name'],
            order_by: 'employee_name asc',
            limit: 0
        }),
        get_allocated_employees(frm)
    ]).then(([list, allocated]) => {

        let changed = false;

        // remove rows of employees that already have an allocation
        if (allocated.size) {
            const rows = frm.doc.hr || [];
            const keep = rows.filter(row => !allocated.has(row.employee));

            if (keep.length !== rows.length) {
                rows.filter(row => allocated.has(row.employee))
                    .forEach(row => frappe.model.clear_doc(row.doctype, row.name));

                keep.forEach((row, i) => {
                    row.idx = i + 1;
                });

                frm.doc.hr = keep;
                changed = true;
            }
        }

        const existing = new Set(
            (frm.doc.hr || []).map(row => row.employee)
        );

        list.forEach(emp => {

            if (existing.has(emp.name) || allocated.has(emp.name)) return;

            frm.add_child('hr', {
                employee: emp.name,
                employee_name: emp.employee_name,
                ...DEFAULT_LEAVES
            });

            changed = true;
        });

        frm.refresh_field('hr');

        if (changed) {
            frm.dirty();
        }
    });
}
