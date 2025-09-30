import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { HrEmployeeActionHelper } from "@hr/views/hr_employee_action_helper/hr_employee_action_helper";

export class HrEmployeeKanbanRenderer extends KanbanRenderer {
    static components = {
        ...KanbanRenderer.components,
        ActionHelper: HrEmployeeActionHelper,
    };
}

export const employeeKanbanView = {
    ...kanbanView,
    Renderer: HrEmployeeKanbanRenderer,
};
registry.category("views").add("hr_employee_kanban", employeeKanbanView);
