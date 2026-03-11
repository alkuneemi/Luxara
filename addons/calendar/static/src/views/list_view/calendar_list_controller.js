/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { user } from "@web/core/user";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
    }

    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }

    /**
     * Display modals to send cancellation emails or chose the deletion type for recurring events.
     */
    async onDeleteSelectedRecords() {
        const declinedAttendeeIds = [];
        let isUnlinkActionRequired = false;
        const unlinkActionEventIds = [];
        for (const record of this.model.root.selection) {
            if (user.isAdmin || user.userId === record.data.user_id.id) {
                unlinkActionEventIds.push(record.resId);
                const partnerIds = record.data.partner_ids.resIds;
                if (!record.data.is_draft && (record.data.recurrency || !(partnerIds.length === 1 && partnerIds[0] === user.partnerId))) {
                    isUnlinkActionRequired = true;
                }
            } else {
                record.selected = false;
                if (record.data.current_attendee && record.data.current_status !== "declined") {
                    declinedAttendeeIds.push(record.data.current_attendee.id);
                }
            }
        }
        if (declinedAttendeeIds.length > 0) {
            await this.orm.call("calendar.attendee", "do_decline", [declinedAttendeeIds]);
        }
        if (isUnlinkActionRequired) {
            await this.orm.call("calendar.event", "action_unlink", [unlinkActionEventIds])
            .then((action) => {
                this.actionService.doAction(action);
            });
        } else if (this.model.root.selection.length > 0) {
            super.onDeleteSelectedRecords(...arguments);
        } else {
            this.actionService.doAction("soft_reload");
        }
    }
}
