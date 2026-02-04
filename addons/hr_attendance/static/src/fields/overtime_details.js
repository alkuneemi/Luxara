import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { _t } from "@web/core/l10n/translation";

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { BadgeTag } from "@web/core/tags_list/badge_tag";

import { Record } from "@web/model/record";
import { Field } from "@web/views/fields/field";

import {
    onWillStart,
    Component,
    useState,
    useRef,
    useEffect,
} from "@odoo/owl";

import { serializeDateTime } from "@web/core/l10n/dates";
import { formatFloatTime } from "@web/views/fields/formatters";

// ---------------------------------------------------------------------
// POPOVER
// ---------------------------------------------------------------------

export class OvertimeDetailsPopover extends Component {
    static template = "hr_attendance.OvertimeDetailsPopover";
    static components = { BadgeTag, Record, Field };

    static props = {
        formattedData: Array,
        recordProps: Function,
        close: Function,
    };

    async onClose() {
        this.props.close();
    }
}

// ---------------------------------------------------------------------
// MAIN COMPONENT
// ---------------------------------------------------------------------

export class OvertimeDetails extends Component {
    static template = "hr_attendance.OvertimeDetails";
    static components = { BadgeTag, Record, Field };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.popover = usePopover(OvertimeDetailsPopover);
        this.state = useState({
            formattedData: [],
        });
        this.widgetRef = useRef("overtimeDetails");
        this.loadRequestId = 0;
        this.initialDataSnapshot = null;
        this.isSaving = false;

        onWillStart(async () => {
            await this.loadDataFromServer();
        });

        useEffect(
            () => {
                this.loadDataFromServer();
            },
            () => [
                this.props.record.data.check_in,
                this.props.record.data.check_out,
            ]
        );
    }

    // ---------------------------------------------------------------------
    // DATA LOADING
    // ---------------------------------------------------------------------

    fetchPlansArgs(props) {
        const record = props.record;
        const args = {};

        if (record.data.employee_id) {
            args.employee_id = record.data.employee_id.id;
        }

        if (record.data.check_in) {
            args.check_in = serializeDateTime(record.data.check_in);
        }

        return args;
    }

    async loadDataFromServer(props = this.props) {
        const requestId = ++this.loadRequestId;
        const args = this.fetchPlansArgs(props);

        if (!args.employee_id || !args.check_in) {
            this.state.formattedData = [];
            return;
        }

        const domain = this.getOvertimeLineDomain(args);
        const fields = this.getOvertimeLineFields();

        const records = await this.orm.searchRead(
            "hr.attendance.overtime.line",
            domain,
            fields
        );

        if (requestId !== this.loadRequestId) return;

        const ruleIds = [...new Set(records.flatMap((r) => r.rule_ids || []))];
        let rules = [];
        if (ruleIds.length) {
            rules = await this.orm.read(
                "hr.attendance.overtime.rule",
                ruleIds,
                ["name"]
            );
        }

        const ruleMap = {};
        for (const r of rules) {
            ruleMap[r.id] = r.name;
        }

        const formatted = records.map((rec) =>
            this.formatOvertimeLine(rec, ruleMap)
        );
        this.state.formattedData = formatted;
        this.initialDataSnapshot = JSON.stringify(formatted);
    }

    getOvertimeLineDomain(args) {
        return [
            ["employee_id", "=", args.employee_id],
            ["time_start", "=", args.check_in],
        ];
    }

    getOvertimeLineFields() {
        return [
            "rule_ids",
            "duration",
            "manual_duration",
            "amount_rate",
        ];
    }

    formatOvertimeLine(record, ruleMap) {
        return {
            id: record.id,
            duration: record.duration,
            manual_duration: record.manual_duration,
            amount_rate: record.amount_rate,
            rule_ids: (record.rule_ids || []).map((id) => ({
                id,
                display_name: ruleMap[id],
            })),
        };
    }

    // ---------------------------------------------------------------------
    // UI
    // ---------------------------------------------------------------------

    async _onOpenPopover() {
        await this.loadDataFromServer();

        this.popover.open(this.widgetRef.el, {
            formattedData: this.state.formattedData,
            recordProps: this.recordProps.bind(this),
        });
    }

    formatDurationOvertime() {
        const total = this.state.formattedData.reduce(
            (sum, line) => sum + (line.manual_duration || 0),
            0
        );
        return formatFloatTime(total);
    }

    // ---------------------------------------------------------------------
    // RECORD PROPS
    // ---------------------------------------------------------------------

    recordProps(line) {
        const overtimeRuleFields = {
            id: { type: "int" },
            display_name: { type: "char" },
        };

        const fields = {
            rule_ids: {
                string: _t("Overtime Rule"),
                type: "many2many",
                relation: "hr.attendance.overtime.rule",
                related: {
                    fields: overtimeRuleFields,
                    activeFields: overtimeRuleFields,
                },
            },
            manual_duration: {
                string: _t("Manual Duration"),
                type: "float_time",
            },
            amount_rate: {
                string: _t("Rate"),
                type: "percentage",
            },
        };
        const values = {
            rule_ids: line.rule_ids || [],
            manual_duration: line.manual_duration,
            amount_rate: line.amount_rate,
        };
        return {
            fields,
            values,
            activeFields: fields,
            resModel: "hr.attendance.overtime.line",
        };
    }

}

// ---------------------------------------------------------------------

export const overtimeDetails = {
    component: OvertimeDetails,
    supportedTypes: ["float"],
};

registry.category("fields").add("overtime_details", overtimeDetails);
