import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/core/dialog/dialog";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { user } from "@web/core/user"


export class ContractEndDateChangeDialog extends Component {
    static template = "hr.ContractEndDateChangeDialog";
    static components = { Dialog, Many2XAutocomplete };
    static props = {
        close: Function,
        record: Object,
    };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            reason: "correction",
            template: { id: false, name: "" },
        });
        this.onTemplateUpdate = this.onTemplateUpdate.bind(this);
    }

    get contractTemplateDomain() {
        return [["employee_id", "=", false], ["company_id", "=", user.activeCompany.id]];
    }

    onTemplateUpdate(records) {
        const record = records?.[0];
        this.state.template.id = record?.id ?? false;
        this.state.template.name = record?.display_name ?? "";
    }

    onCorrectContract() {
        this.props.close({ reason: "correction" });
    }

    async onEndCollaboration() {
        try {
            const action = await this.orm.call(
                "hr.employee",
                "action_new_departure",
                [[this.props.record.resId]],
            );
            action.views = [[false, "form"]];
            action.context = {
                ...(action.context || {}),
                default_dismissal_date: this.props.record?.data?.contract_date_end || false,
            };

            this.props.close({ reason: "end_collaboration", action });
        } catch (error) {
            console.error("Failed to end collaboration:", error);
        }
    }

    onDiscard() {
        this.props.close({ reason: "discard" });
    }

    onNewContract() {
        this.props.close({
            reason: "new_contract",
            contractTemplateId: this.state.template.id || false,
        });
    }
}
