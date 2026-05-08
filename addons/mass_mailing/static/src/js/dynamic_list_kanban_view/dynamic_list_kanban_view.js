import { kanbanView } from "@web/views/kanban/kanban_view";
import { registry } from "@web/core/registry";
import { DynamicListKanbanController } from "./dynamic_list_kanban_controller";

export const DynamicListKanbanView = {
    ...kanbanView,
    Controller: DynamicListKanbanController,
};
registry.category("views").add("dynamic_list_kanban_view", DynamicListKanbanView);
