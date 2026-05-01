import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { getFieldFromRegistry } from "@web/views/fields/field";

import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { ListRenderer } from "@web/views/list/list_renderer";

import {
    Component,
    EventBus,
    useState,
    useRef,
    onWillStart,
    useEffect,
    useSubEnv,
} from "@odoo/owl";

import { serializeDateTime } from "@web/core/l10n/dates";
import { formatFloatTime } from "@web/views/fields/formatters";

const RES_MODEL = "hr.attendance.overtime.line";
const RULE_MODEL = "hr.attendance.overtime.rule";

export class OvertimeDetailsPopover extends Component {
    static template = "hr_attendance.OvertimeDetailsPopover";
    static components = { ListRenderer };

    static props = {
        close: Function,
        rows: Array,
    };

    setup() {
        useSubEnv({
            config: { viewId: 999999 },
        });

        const fields = {
            rule_ids: {
                name:     "rule_ids",
                type:     "many2many",
                string:   "Applied Rules",
                relation: RULE_MODEL,
            },
            manual_duration: {
                name:   "manual_duration",
                type:   "float",
                string: "Overtime",
                widget: "float_time",
            },
            amount_rate: {
                name:   "amount_rate",
                type:   "float",
                string: "Overtime Pay Rate",
            },
        };

        const activeFields = {
            rule_ids: {
                name:             "rule_ids",
                type:             "many2many",
                string:           "Applied Rules",
                relation:         RULE_MODEL,
                widget:           "many2many_tags",
                field:            getFieldFromRegistry("many2many", "many2many_tags", "list", undefined),
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
            },
            manual_duration: {
                name:             "manual_duration",
                type:             "float",
                string:           "Overtime",
                widget:           "float_time",
                field:            getFieldFromRegistry("float", "float_time", "list", undefined),
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
            },
            amount_rate: {
                name:             "amount_rate",
                type:             "float",
                string:           "Overtime Pay Rate",
                widget:           undefined,
                field:            getFieldFromRegistry("float", undefined, "list", undefined),
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
            },
        };

        const columns = Object.entries(fields).map(([name, field]) => ({
            type:     "field",
            name,
            id:       name,
            string:   field.string,
            label:    field.string,
            hasLabel: true,
            optional: false,
            groupby:  false,
            sortable: false,
            attrs:    {},
            options:  {},
            widget:   activeFields[name].widget,
            field:    activeFields[name].field,
        }));

        const archInfo = {
            columns,
            activeFields,
            headerButtons: [],
            activeActions: {
                type:      "list",
                edit:      false,
                create:    false,
                delete:    false,
                duplicate: false,
            },
            editable:             false,
            type:                 "list",
            groupBy:              [],
            defaultOrder:         [],
            limit:                80,
            countLimit:           80,
            creates:              [],
            controls:             [],
            decorations:          [],
            optionalActiveFields: {},
            expand:               false,
            rawExpand:            false,
            className:            "",
            noContentHelp:        "",
        };

        const bus = new EventBus();

        const model = {
            bus,
            useSampleModel: false,
            notify:         () => {},
            config: {
                resModel:     RES_MODEL,
                fields,
                activeFields,
                editable:     false,
            },
            root: null,
        };

        const makeRuleRecord = (id, name) => ({
            id,
            resId:                     id,
            display_name:              name,
            selected:                  false,
            isInEdition:               false,
            canBeAbandoned:            false,
            isFieldInvalid:            () => false,
            evalContextWithVirtualIds: {},
            isDirty:                   false,
            isNew:                     false,
            isVirtual:                 false,
            fields:                    { display_name: { name: "display_name", type: "char" } },
            activeFields:              {},
            data:                      { id, display_name: name },
            model: {
                bus:            new EventBus(),
                useSampleModel: false,
                notify:         () => {},
                root:           null,
                config: {
                    resModel:     RULE_MODEL,
                    fields:       {},
                    activeFields: {},
                    editable:     false,
                },
            },
        });

        const records = this.props.rows.map((row, index) => {
            const ruleRecords = Array.isArray(row.rule_ids)
                ? row.rule_ids.map((r) =>
                    Array.isArray(r)
                        ? makeRuleRecord(r[0], r[1])
                        : makeRuleRecord(r, String(r))
                )
                : [];

            return {
                id:                        row.id,
                resId:                     row.id,
                selected:                  false,
                isInEdition:               false,
                canBeAbandoned:            false,
                isFieldInvalid:            () => false,
                evalContextWithVirtualIds: {},
                isDirty:                   false,
                isNew:                     false,
                isVirtual:                 false,
                index,
                fields,
                activeFields,
                model,
                data: {
                    rule_ids: {
                        currentIds:   ruleRecords.map((r) => r.id),
                        records:      ruleRecords,
                        display_name: ruleRecords.map((r) => r.display_name).join(", "),
                        resModel:     RULE_MODEL,
                        nameField:    "display_name",
                    },
                    manual_duration: row.manual_duration || 0,
                    amount_rate:     row.amount_rate     || 0,
                },
            };
        });

        this.fakeList = {
            records,
            count:           records.length,
            offset:          0,
            limit:           records.length,
            resModel:        RES_MODEL,
            fields,
            fieldNames:      Object.keys(fields),
            activeFields,
            isGrouped:       false,
            groupBy:         [],
            groups:          [],
            selection:       [],
            orderBy:         [],
            editedRecord:    null,
            isM2MEditable:   false,
            isDirty:         false,
            hasLimitedCount: false,
            editable:        false,
            canResequence:   () => false,
            toggleSelection: () => {},
            leaveEditMode:   () => {},
            model,
        };

        model.root = this.fakeList;
        this.fakeArchInfo = archInfo;
    }

    get rendererProps() {
        return {
            list:           this.fakeList,
            archInfo:       this.fakeArchInfo,
            readonly:       true,
            allowSelectors: false,
            cycleOnTab:     false,
            noContentHelp:  "",
            openRecord:     () => {},
        };
    }
}

export class OvertimeDetails extends Component {
    static template = "hr_attendance.OvertimeDetails";
    static props = { ...standardFieldProps };

    setup() {
        this.orm     = useService("orm");
        this.popover = usePopover(OvertimeDetailsPopover);

        this.state = useState({
            totalDuration: 0,
            resIds:        [],
        });

        this.widgetRef     = useRef("overtimeDetails");
        this.loadRequestId = 0;

        onWillStart(() => this.loadDataFromServer());

        useEffect(
            () => { this.loadDataFromServer(); },
            () => [
                this.props.record.data.check_in,
                this.props.record.data.check_out,
            ]
        );
    }

    async loadDataFromServer() {
        const requestId = ++this.loadRequestId;
        const { employee_id, check_in } = this.props.record.data;

        if (!employee_id || !check_in) {
            this.state.totalDuration = 0;
            this.state.resIds        = [];
            return;
        }

        const lines = await this.orm.searchRead(
            RES_MODEL,
            [
                ["employee_id", "=", employee_id.id],
                ["time_start",  "=", serializeDateTime(check_in)],
            ],
            ["id", "manual_duration"]
        );

        if (requestId !== this.loadRequestId) return;

        this.state.resIds        = lines.map((l) => l.id);
        this.state.totalDuration = lines.reduce((s, l) => s + (l.manual_duration || 0), 0);
    }

    get formattedTotal() {
        return formatFloatTime(this.state.totalDuration);
    }

    onKeyDown(ev) {
        if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            this.onClickDetails();
        }
    }

    async onClickDetails() {
        await this.loadDataFromServer();

        const rows = await this.orm.searchRead(
            RES_MODEL,
            [["id", "in", this.state.resIds]],
            ["id", "rule_ids", "manual_duration", "amount_rate"]
        );

        const allRuleIds = [...new Set(rows.flatMap((r) => r.rule_ids))];

        let ruleNameMap = {};
        if (allRuleIds.length) {
            const ruleRecords = await this.orm.read(
                RULE_MODEL,
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
    }
}

export const overtimeDetails = {
    component:      OvertimeDetails,
    supportedTypes: ["float"],
};

registry.category("fields").add("overtime_details", overtimeDetails);
