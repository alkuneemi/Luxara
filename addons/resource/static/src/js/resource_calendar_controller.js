import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";

/**
 * Custom dialog component (3 actions)
 */
class WorkingScheduleDialog extends Component {
    static template = "my_module.WorkingScheduleDialog";
    static props = {
        workResourcesCount: Number,
        confirmUpdate: Function,
        createNew: Function,
        cancel: Function,
    };
}

/**
 * Controller
 */
export class ResourceCalendarController extends formView.Controller {
    setup() {
        console.log(">> ResourceCalendarController setup");
        super.setup();
        this.dialog = useService("dialog");
        this.action = useService("action");
        this.orm = useService("orm");

        this.forceSave = false;
    }

    async onRecordSaved(record) {
        console.log(">> onRecordSaved");
        await super.onRecordSaved(...arguments);
    }

    async onWillSaveRecord(record) {
        console.log(">> onWillSaveRecord");
        if (this.forceSave) {
            return true;
        }

        const workResourcesCount = record.data.work_resources_count || 0;
        console.log(">> workResourcesCount", workResourcesCount);

        // no warning needed
        if (workResourcesCount <= 1) {
            console.log(">> no warning needed");
            return true;
        }

        return new Promise((resolve) => {
            const dialog = this.dialog.add(WorkingScheduleDialog, {
                workResourcesCount,

                confirmUpdate: () => {
                    this.forceSave = true;
                    dialog();
                    resolve(true);
                },

                cancel: () => {
                    record.model.root.discard();
                    dialog();
                    resolve(false);
                },

                createNew: async () => {
                    const changes = record.getChanges();
                    const currentId = record.resId;

                    console.log(">> createNew with changes", changes);

                    // 2. Call copy and pass the UI changes as 'default' values 
                    // so the new record is created with the user's modifications.
                    const newIds = await this.orm.call(
                        "resource.calendar",
                        "copy",
                        [[currentId]],
                        { default: changes } 
                    );
                    const newId = Array.isArray(newIds) ? newIds[0] : newIds;

                    // 3. Step Two: Apply the UI changes to the newly created record
                    // We use 'write' because it perfectly handles the Command arrays from getChanges()
                    //if (Object.keys(changes).length > 0) {
                    //    await this.orm.write("resource.calendar", [newId], changes);
                    //}

                    // 3. Now it is safe to revert UI changes on the original record
                    record.model.root.discard(); 
                    dialog();
                    resolve(false);

                    // 4. Link to employee if navigated from one
                    const context = record.context || {};
                    if (context.active_model === "hr.employee" && context.active_id) {
                        await this.orm.write("hr.employee", [parseInt(context.active_id)], {
                            resource_calendar_id: newId,
                        });
                    }

                    // 5. Redirect to the new record
                    await this.action.doAction({
                        type: "ir.actions.act_window",
                        res_model: "resource.calendar",
                        res_id: newId,
                        views: [[false, "form"]],
                        target: "current",
                    });
                },
            });
        });
    }
}

registry.category("views").add("resource_calendar_form", {
    ...formView,
    Controller: ResourceCalendarController,
});
