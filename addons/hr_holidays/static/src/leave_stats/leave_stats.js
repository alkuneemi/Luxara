import { useState } from "@web/owl2/utils";
import { serializeDateTime, serializeDate } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { formatFloatTime } from "@web/views/fields/formatters";
import { Component, onWillStart } from "@odoo/owl";
import { standardWidgetProps } from "@web/views/widgets/standard_widget_props";
import { _t } from "@web/core/l10n/translation";
import { ColorPickerField } from "@web/views/fields/color_picker/color_picker_field";
const { DateTime } = luxon;

export class LeaveStatsComponent extends Component {
    static template = "hr_holidays.LeaveStatsComponent";
    static components = {
        ColorPickerField
    };
    static props = { ...standardWidgetProps};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            leaves: [],
            departmentLeavesIds: [],
            nbEmployee: 0,
            date: DateTime,
            department: null,
            employee: null,
            type: null,
            department_name: null,
        });
        this.date_format = {year: "numeric", month: "2-digit", day: "2-digit"};
        this.hour_format = {hour: "2-digit", minute: "2-digit"};
        this.state.date_from = this.props.record.data.request_date_from || DateTime.now();
        this.state.date_to = this.props.record.data.request_date_to || DateTime.now();
        this.state.employee = this.props.record.data.employee_id;
        this.state.department = this.props.record.data.department_id;

        onWillStart(async () => {
            await this.loadLeaves(this.state.employee);
            await this.loadDepartmentLeaves(
                this.state.department,
                this.state.employee
            );
        });

        useRecordObserver(async (record) => {
            const dateFrom = record.data.date_from || DateTime.now();
            const dateTo = record.data.date_to || DateTime.now();
            const dateChanged = !this.state.date_from.equals(dateFrom) || !this.state.date_to.equals(dateTo);
            this.state.date_from = dateFrom
            this.state.date_to = dateTo
            const employee = record.data.employee_id;
            const department = record.data.department_id;
            const proms = [];
            if (
                dateChanged ||
                (employee && (this.state.employee && this.state.employee.id) !== employee.id)
            ) {
                proms.push(this.loadLeaves(employee));
            }
            if (
                dateChanged ||
                (department &&
                    (this.state.department && this.state.department.id) !== department.id)
            ) {
                proms.push(this.loadDepartmentLeaves(department, employee));
            }
            await Promise.all(proms);
            this.state.date_from = dateFrom;
            this.state.employee = employee;
            this.state.department = department;
            if (this.state.department) {
                const department_name_array = this.state.department.display_name.split('/');
                this.state.department_name = department_name_array.pop();
            }
        });
    }

    get thisYear() {
        return this.state.date_from.toFormat("yyyy");
    }

    async loadDepartmentLeaves(department, employee) {
        if (!(department && employee)) {
            this.state.departmentLeavesIds = [];
            this.state.nbEmployee = 0;
            return;
        }

        const dateFrom = serializeDateTime(this.state.date_from);
        const dateTo = serializeDateTime(this.state.date_to);
        const leaves = await this.orm.webSearchRead(
            "hr.leave",
            [
                ["department_id", "=", department.id],
                ["state", "=", "validate"],
                ["employee_id", "!=", employee.id],
                ["date_from", "<=", dateTo],
                ["date_to", ">=", dateFrom],
            ],
            {
                specification: {
                    employee_id: { fields: { display_name: {} } },
                    id: {}
                },
            }
        );
        if (!leaves) {
            return;
        }
        this.state.departmentLeavesIds = leaves.records.map((leave) => leave.id);
        this.state.nbEmployee = new Set(leaves.records.map((leave) => leave.employee_id )).size;
    }

    async action_department_leaves(){
        if (!this.state.departmentLeavesIds) {
            return;
        }
        return this.action.doAction({
            name: _t("View Overlaps"),
            type: "ir.actions.act_window",
            res_model: "hr.leave",
            views: [[false, "gantt"]],
            domain: [["id", "in", this.state.departmentLeavesIds]],
            context: {
                default_start_date: serializeDate(this.props.record.data.request_date_from),
                default_stop_date: serializeDate(this.props.record.data.request_date_to),
            },
            target: "current",
        });
    }

    async loadLeaves(employee) {
        if (!employee) {
            this.state.leaves = [];
            return;
        }
        const allocation_data = await this.orm.call("hr.work.entry.type", "get_allocation_data_request", [this.state.date_from], { context: { employee_id: employee.id } })
        this.state.leaves = allocation_data
            .filter((data) => data[1].leaves_approved > 0)
            .map((data) => {
                let work_entry_data = {}
                work_entry_data.data = data[0]
                work_entry_data.unit_of_measure = data[1].unit_of_measure
                if (data[1].unit_of_measure == 'hour') {
                    work_entry_data.leaves_approved = data[1].leaves_approved ? formatFloatTime(data[1].leaves_approved.toFixed(2)) : 0
                    work_entry_data.max_leaves = data[1].max_leaves ? formatFloatTime(data[1].max_leaves.toFixed(2)) : 0
                    work_entry_data.remaining_leaves = data[1].remaining_leaves ? formatFloatTime(data[1].remaining_leaves.toFixed(2)) : 0
                } else {
                    work_entry_data.leaves_approved = data[1].leaves_approved
                    work_entry_data.max_leaves = data[1].max_leaves
                    work_entry_data.remaining_leaves = data[1].remaining_leaves
                }
                return work_entry_data
            });
    }
    arrangeData(leaves) {
        return leaves.map((leave) => {
            let resultLeave = {};
            resultLeave.data = {
                id: leave.id,
                color: leave.color,
                work_entry_type_id: leave.work_entry_type_id,
                work_entry_type_request_unit: leave.work_entry_type_request_unit,
                number_of_hours: formatFloatTime(Number(leave.number_of_hours.toFixed(2))),
                number_of_days: Number(leave.number_of_days.toFixed(2)),
                max_leaves: leave.max_leaves,
                virtual_remaining_leaves: leave.virtual_remaining_leaves,
            }
            return resultLeave;
        })
    }
}

export const leaveStatsComponent = {
    component: LeaveStatsComponent,
    fieldDependencies: [
        { name: "employee_id", type: "many2one" },
        { name: "date_from", type: "datetime" },
        { name: "date_to", type: "datetime" },
        { name: "department_id", type: "many2one" },
    ],
};
registry.category("view_widgets").add("hr_leave_stats", leaveStatsComponent);
