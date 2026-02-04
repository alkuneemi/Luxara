import { patch } from "@web/core/utils/patch";
import { OvertimeDetails } from "@hr_attendance/fields/overtime_details";


patch(OvertimeDetails.prototype, {
    getOvertimeLineFields() {
        return [...super.getOvertimeLineFields(...arguments), "compensable_as_leave", "leave_compensation_rate"];
    },
    formatOvertimeLine(record, ruleMap) {
        return {
            ...super.formatOvertimeLine(record, ruleMap),
            compensable_as_leave: record.compensable_as_leave,
            leave_compensation_rate: record.leave_compensation_rate,
        };
    },

    // Extend recordProps
    recordProps(line) {
        const result = super.recordProps(...arguments);
        result.fields.compensable_as_leave = {
            string: "Compensable as Time Off",
            type: "boolean",
        };

        result.fields.leave_compensation_rate = {
            string: "Leave Earn Rate",
            type: "percentage",
        };

        result.values.compensable_as_leave =
            line.compensable_as_leave;

        result.values.leave_compensation_rate =
            line.leave_compensation_rate;

        result.activeFields.compensable_as_leave =
            result.fields.compensable_as_leave;

        return result;
    },

    serializeOvertimeLine(line) {
        return {
            ...super.serializeOvertimeLine(...arguments),
            compensable_as_leave: line.compensable_as_leave,
            leave_compensation_rate: line.leave_compensation_rate,
        };
     },
});
