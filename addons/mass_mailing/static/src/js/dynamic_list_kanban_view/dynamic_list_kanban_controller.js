import { useService } from "@web/core/utils/hooks";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { DynamicListTemplatePickerDialog } from "../../components/dynamic_list_picker_dialog/dynamic_list_template_picker_dialog";

export class DynamicListKanbanController extends KanbanController {
    setup() {
        super.setup();
        this.dialog = useService("dialog");
    }
    /**
     * @override
     */
    async createRecord() {
        this.dialog.add(DynamicListTemplatePickerDialog, {});
    }
}
