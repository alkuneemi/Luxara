import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";


defineMailModels();

// ─────────────────────────────────────────────────────────────────────────────
// Models
// ─────────────────────────────────────────────────────────────────────────────

class HrEmployee extends models.Model {
    _name = "hr.employee";

    name = fields.Char();

    _records = [{ id: 1, name: "Mitchell Admin" }];
}

class HrAttendanceOvertimeRule extends models.Model {
    _name = "hr.attendance.overtime.rule";

    name = fields.Char();

    _records = [{ id: 1, name: "Weekday Rule" }];
}

class HrAttendanceOvertimeLine extends models.Model {
    _name = "hr.attendance.overtime.line";

    employee_id     = fields.Many2one({ relation: "hr.employee" });
    time_start      = fields.Datetime();
    duration        = fields.Float();
    manual_duration = fields.Float();
    amount_rate     = fields.Float();
    rule_ids        = fields.Many2many({ relation: "hr.attendance.overtime.rule" });

    _records = [
        {
            id: 11,
            employee_id: 1,
            time_start: "2026-03-24 08:00:00",
            duration: 1,
            manual_duration: 1,
            amount_rate: 1,
            rule_ids: [1],
        },
        {
            id: 12,
            employee_id: 1,
            time_start: "2026-03-25 08:00:00",
            duration: 1,
            manual_duration: 1,
            amount_rate: 1,
            rule_ids: [1],
        },
    ];
}

class HrAttendance extends models.Model {
    _name = "hr.attendance";

    employee_id     = fields.Many2one({ relation: "hr.employee" });
    check_in        = fields.Datetime();
    check_out       = fields.Datetime();
    overtime_status = fields.Selection({
        selection: [
            ["to_approve", "To Approve"],
            ["approved",   "Approved"],
            ["refused",    "Refused"],
        ],
    });
    overtime_hours = fields.Float();

    _records = [
        {
            id: 1,
            employee_id: 1,
            check_in:  "2026-03-24 08:00:00",
            check_out: "2026-03-24 18:00:00",
            overtime_status: "to_approve",
            overtime_hours: 1,
        },
        {
            id: 2,
            employee_id: 1,
            check_in:  "2026-03-25 08:00:00",
            check_out: "2026-03-25 18:00:00",
            overtime_status: "approved",
            overtime_hours: 1,
        },
    ];
}

defineModels([HrEmployee, HrAttendance, HrAttendanceOvertimeLine, HrAttendanceOvertimeRule]);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────
async function mountAttendanceForm(resId) {
    await mountView({
        type: "form",
        resModel: "hr.attendance",
        resId,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="employee_id"     invisible="1"/>
                        <field name="check_in"        invisible="1"/>
                        <field name="check_out"       invisible="1"/>
                        <field name="overtime_status" invisible="1"/>
                        <field name="overtime_hours"  widget="overtime_details"/>
                    </group>
                </sheet>
            </form>`,
    });
}

async function openOvertimePopover() {
    await contains(".o_field_widget[name='overtime_hours'] [tabindex='0']").click();
    await animationFrame();
}

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

test.tags("desktop");
test("form: closing overtime details does not write", async () => {
    onRpc("hr.attendance.overtime.line", "write", () => expect.step("write"));
    await mountAttendanceForm(1);
    await openOvertimePopover();
    expect(".popover .popover-body tbody tr").toHaveCount(1);
    await contains(".o_form_view").click();
    await animationFrame();

    expect.verifySteps([]);
});

test.tags("desktop");
test("form: overtime details popover fields are all readonly", async () => {
    onRpc("hr.attendance.overtime.line", "write", () => expect.step("write"));
    await mountAttendanceForm(1);
    await openOvertimePopover();
    expect(".popover .popover-body tbody tr").toHaveCount(1);
    // No editable inputs should exist anywhere in the popover
    expect(".popover tbody input").toHaveCount(0);
    await contains(".o_form_view").click();
    await animationFrame();

    // No write should have been triggered since everything is readonly
    expect.verifySteps([]);
});

test.tags("desktop");
test("form: approved overtime details are readonly", async () => {
    await mountAttendanceForm(2);
    await openOvertimePopover();
    expect(".popover .popover-body tbody tr").toHaveCount(1);
    // No editable inputs should exist for any column
    expect(".popover tbody input").toHaveCount(0);
});

test.tags("desktop");
test("form: to_approve overtime details are readonly", async () => {
    await mountAttendanceForm(1);
    await openOvertimePopover();
    expect(".popover .popover-body tbody tr").toHaveCount(1);
    // No editable inputs should exist regardless of overtime_status
    expect(".popover tbody input").toHaveCount(0);
});
