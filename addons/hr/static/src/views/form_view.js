import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { serializeDate } from "@web/core/l10n/dates";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";
import { FormRenderer } from "@web/views/form/form_renderer";
import { ContractEndDateChangeDialog } from "@hr/components/contract_end_date_change_dialog/contract_end_date_change_dialog";

export class EmployeeFormController extends FormController {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this._acknowledgedContractDateEnd = null;
    }

    onRecordChanged(record, changes) {
        super.onRecordChanged(record, changes);

        const contractDateEnd = record.data.contract_date_end;
        const previousContractDateEnd = record._values?.contract_date_end;
        const contractDateStart = record.data.contract_date_start;
        const previousContractDateStart = record._values?.contract_date_start;
        const hasDeparture = record.data.departure_id;

        const alreadyAcknowledged = this._acknowledgedContractDateEnd
            ? this._acknowledgedContractDateEnd === contractDateEnd
            : false;

        if (
            previousContractDateStart !== contractDateStart
            || previousContractDateEnd === contractDateEnd
            || !contractDateEnd
            || hasDeparture
            || alreadyAcknowledged
        ) {
            return;
        }

        this.dialogService.add(ContractEndDateChangeDialog, {
            record: record,
        }, {
            onClose: async (result) => {
                switch (result?.reason) {
                    case "correction":
                        this._acknowledgedContractDateEnd = contractDateEnd;
                        await record.update({ fixed_term: true });
                        break;
                    case "new_contract": {
                        const newContractDateStart = contractDateEnd.plus({ days: 1 });
                        let newContractDateEnd = false;
                        if (previousContractDateEnd && contractDateEnd < previousContractDateEnd) {
                            newContractDateEnd = previousContractDateEnd;
                        }
                        await record.save();
                        try {
                            const version_id = await this.orm.call("hr.employee", "create_version", [
                                record.resId,
                                {
                                    date_version: serializeDate(newContractDateStart),
                                    contract_date_start: serializeDate(newContractDateStart),
                                    contract_date_end: newContractDateEnd ? serializeDate(newContractDateEnd) : false,
                                    contract_template_id: result.contractTemplateId,
                                },
                            ]);
                            await record.model.load({
                                context: {
                                    ...(record.model.env.searchModel?.context || {}),
                                    version_id,
                                },
                            });
                        } catch (error) {
                            console.error("Failed to create a new contract:", error);
                        }
                        break;
                    }
                    case "end_collaboration":
                        this.actionService.doAction(result.action, {
                            onClose: async () => {
                                await record.model.load();
                            },
                        });
                    case "discard":
                    default:
                        await record.update({ contract_date_end: this._acknowledgedContractDateEnd || false });
                        break;
                }
            },
        });
    }
}

export class EmployeeFormRenderer extends FormRenderer {}

registry.category("views").add("hr_employee_form", {
    ...formView,
    Controller: EmployeeFormController,
    Renderer: EmployeeFormRenderer,
});
