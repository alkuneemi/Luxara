import { FormController } from "@web/views/form/form_controller";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";

export class CalendarFormController extends FormController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    /**
     * @override
     */
    async beforeExecuteActionButton(clickParams) {
        const action = clickParams.name;
        if (action === "clear_videocall_location") {
            this.model.root.clearLocation();
            return false;
        } else if (action === "set_discuss_videocall_location") {
            this.model.root.setLocation();
            return false;
        }
        return super.beforeExecuteActionButton(...arguments);
    }

    /**
     * @override
     *
     * If the event is deleted by the organizer, the event is deleted, otherwise it is declined.
     */
    deleteRecord() {
        console.log("pass inside the new open cancel wizard");
        const record = this.model.root;
        this.model.openCancelWizard(
            record.resId,
            record.data,
            record.data.partner_ids,
            super.deleteRecord,
            arguments,
            {type: "ir.actions.act_url", target: "self", url: "/odoo/calendar"}
        )
    }

    shouldAskInvitationsSending(record) {
        return record.newPartners.length > 0 && record.data.start >= luxon.DateTime.now() && !record.data.is_draft;
    }

    async onRecordSaved(record, changes) {
        await super.onRecordSaved(...arguments);
        record.newPartners = (changes.partner_ids ?? []).reduce((acc, partner) => {
            if (partner[0] === 4) {
                acc.push(partner[1]);
            }
            return acc;
        }, []);
        if (this.shouldAskInvitationsSending(record)) {
            const actionOpenInviteWizard = await this.orm.call("calendar.event", "action_open_invite_wizard", [record.resId, record.newPartners]);
            if (actionOpenInviteWizard && actionOpenInviteWizard.context) {
                this.actionService.doAction(actionOpenInviteWizard);
            }
        }
    }
}
