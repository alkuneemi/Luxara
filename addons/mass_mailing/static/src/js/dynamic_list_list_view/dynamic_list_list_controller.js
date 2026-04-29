import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { DynamicListTemplatePickerDialog } from "../../components/dynamic_list_picker_dialog/dynamic_list_template_picker_dialog";

export class DynamicListListController extends ListController {
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
