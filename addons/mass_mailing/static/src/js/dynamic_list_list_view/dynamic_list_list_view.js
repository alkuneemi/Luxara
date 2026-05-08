import { listView } from "@web/views/list/list_view";
import { DynamicListListController } from "./dynamic_list_list_controller";
import { registry } from "@web/core/registry";

export const DynamicListListView = {
    ...listView,
    Controller: DynamicListListController,
};

registry.category("views").add("dynamic_list_list_view", DynamicListListView);
