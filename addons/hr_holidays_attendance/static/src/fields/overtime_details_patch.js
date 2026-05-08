import { patch } from "@web/core/utils/patch";
import { OvertimeDetails, OvertimeDetailsPopover } from "@hr_attendance/fields/overtime_details";
import { getFieldFromRegistry } from "@web/views/fields/field";

const EXTRA_FIELDS = ["compensable_as_leave", "leave_compensation_rate"];

// ── 1. Patch the main widget to fetch extra fields ────────────────────────────
patch(OvertimeDetails.prototype, {
    async onClickDetails() {
        await this.loadDataFromServer();

        const rows = await this.orm.searchRead(
            "hr.attendance.overtime.line",
            [["id", "in", this.state.resIds]],
            ["id", "rule_ids", "manual_duration", "amount_rate", ...EXTRA_FIELDS]
        );

        const allRuleIds = [...new Set(rows.flatMap((r) => r.rule_ids))];

        let ruleNameMap = {};
        if (allRuleIds.length) {
            const ruleRecords = await this.orm.read(
                "hr.attendance.overtime.rule",
                allRuleIds,
                ["id", "name"]
            );
            ruleNameMap = Object.fromEntries(ruleRecords.map((r) => [r.id, r.name]));
        }

        const enrichedRows = rows.map((row) => ({
            ...row,
            rule_ids: (row.rule_ids || []).map((id) => [id, ruleNameMap[id] || String(id)]),
        }));

        this.popover.open(this.widgetRef.el, { rows: enrichedRows });
    },
});

// ── 2. Patch the popover to add extra columns ─────────────────────────────────
patch(OvertimeDetailsPopover.prototype, {
    setup() {
        super.setup(...arguments);

        // Extend fields
        this.fakeList.fields.compensable_as_leave = {
            name:   "compensable_as_leave",
            type:   "boolean",
            string: "Compensable as Time Off",
        };
        this.fakeList.fields.leave_compensation_rate = {
            name:   "leave_compensation_rate",
            type:   "float",
            string: "Leave Earn Rate",
        };

        // Extend activeFields
        this.fakeList.activeFields.compensable_as_leave = {
            name:             "compensable_as_leave",
            type:             "boolean",
            string:           "Compensable as Time Off",
            widget:           undefined,
            field:            getFieldFromRegistry("boolean", undefined, "list", undefined),
            context:          "{}",
            domain:           undefined,
            help:             undefined,
            onChange:         false,
            forceSave:        false,
            options:          {},
            decorations:      {},
            attrs:            {},
            readonly:         true,
            required:         undefined,
            invisible:        undefined,
            column_invisible: undefined,
        };
        this.fakeList.activeFields.leave_compensation_rate = {
            name:             "leave_compensation_rate",
            type:             "float",
            string:           "Leave Earn Rate",
            widget:           "percentage",
            field:            getFieldFromRegistry("float", "percentage", "list", undefined),
            context:          "{}",
            domain:           undefined,
            help:             undefined,
            onChange:         false,
            forceSave:        false,
            options:          {},
            decorations:      {},
            attrs:            {},
            readonly:         true,
            required:         undefined,
            invisible:        undefined,
            column_invisible: undefined,
        };

        // Extend columns in archInfo
        this.fakeArchInfo.columns.push(
            {
                type:     "field",
                name:     "compensable_as_leave",
                id:       "compensable_as_leave",
                string:   "Compensable as Time Off",
                label:    "Compensable as Time Off",
                hasLabel: true,
                optional: false,
                groupby:  false,
                sortable: false,
                attrs:    {},
                options:  {},
                widget:   undefined,
                field:    this.fakeList.activeFields.compensable_as_leave.field,
            },
            {
                type:     "field",
                name:     "leave_compensation_rate",
                id:       "leave_compensation_rate",
                string:   "Leave Earn Rate",
                label:    "Leave Earn Rate",
                hasLabel: true,
                optional: false,
                groupby:  false,
                sortable: false,
                attrs:    {},
                options:  {},
                widget:   "percentage",
                field:    this.fakeList.activeFields.leave_compensation_rate.field,
            }
        );

        // Extend fieldNames
        this.fakeList.fieldNames.push("compensable_as_leave", "leave_compensation_rate");

        // Extend each record's data
        this.fakeList.records.forEach((record, index) => {
            const row = this.props.rows[index];
            record.data.compensable_as_leave    = row.compensable_as_leave    ?? false;
            record.data.leave_compensation_rate = row.leave_compensation_rate ?? 0;
            record.fields      = this.fakeList.fields;
            record.activeFields = this.fakeList.activeFields;
        });
    },
});
