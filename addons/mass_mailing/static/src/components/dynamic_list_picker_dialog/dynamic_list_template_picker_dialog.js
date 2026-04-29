import { Component, onWillStart } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@web/owl2/utils";

export class DynamicListTemplatePickerDialog extends Component {
    static template = "mass_mailing.DynamicListTemplatePickerDialog";
    static components = {
        Dialog,
    };
    static props = {
        close: { type: Function, optional: true },
    };

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.templates = useState({});

        onWillStart(async () => {
            const templates = await this.orm.call(
                "mailing.filter",
                "get_dynamic_list_templates_info",
                []
            );

            Object.assign(this.templates, templates);
        });
    }

    /**
     * Opens a dynamic list creation form with the domain of the selected template
     * set by default.
     *
     * @param {string} templateName the template identifier. Eg: 'recent_sign_ups'.
     */
    async onChooseListTemplate(templateName) {
        const functionName = this.templates[templateName].function;
        const domain = this.templates[templateName].domain;
        const title = this.templates[templateName].title;

        if (!functionName) {
            return;
        }
        const action = await this.orm.call("mailing.filter", functionName, [
            templateName,
            domain,
            title,
        ]);
        if (!action) {
            return;
        }
        this.action.doAction(action);
        this.props.close();
    }
}
