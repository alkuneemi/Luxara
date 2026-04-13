/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list/list_controller";
import { useAskRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { user } from "@web/core/user";

export class CaledarListController extends ListController {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.askRecurrenceUpdatePolicy = useAskRecurrenceUpdatePolicy();
    }

    get modelOptions() {
        return {
            ...super.modelOptions,
            lazy: false,
        };
    }

    /**
     * Deletes selected records with handling for recurring events.
     */
//    async onDeleteSelectedRecords() {
//        const selectedRecords = this.model.root.selection;
//        let recurrenceUpdate = false;
//        if (selectedRecords.length == 1 && selectedRecords[0]?.data.recurrency) {
//            recurrenceUpdate = await this.askRecurrenceUpdatePolicy();
//            console.log("get closer");
//            if (recurrenceUpdate) {
//                console.log("Will archive")
//                await this.orm.call(this.model.root.resModel, "action_mass_archive", [[selectedRecords[0]?.resId], recurrenceUpdate]);
//                this.model.load();
//            }
//        } else {
//            console.log("will delete");
//            super.onDeleteSelectedRecords(...arguments);
//        }
//    }

    openRecurringDeletionWizard(calendarEventId, attendeeId) {
        this.actionService.doAction(
            {
                type: "ir.actions.act_window",
                res_model: "calendar.popover.delete.wizard",
                views: [[false, "form"]],
                view_mode: "form",
                name: "Delete Recurring Event",
                context: {
                    default_calendar_event_id: calendarEventId,
                    default_attendee_id: attendeeId,
                    form_view_ref: 'calendar.calendar_popover_delete_view',
                },
                target: "new",
            },
            {
                onClose: () => {
                    this.model.load();
                },
            }
        );
    }

    async onDeleteSelectedRecords() {
        const selectedRecords = this.model.root.selection;
        const userAttendeesDetails = await this.orm.call("res.partner", "get_attendee_detail", [
            user.partnerId,
            selectedRecords.map((record) => record.resId),
        ]);
        if (selectedRecords.length == 1 && user.userId === selectedRecords[0].data.user_id.id) {
            console.log("is passing to delete only one record")
            const record = selectedRecords[0];
            const partnerIds = record.data.partner_ids.resIds;
            const userAttendeeId = userAttendeesDetails[0].attendee_id;
            if (record.data.recurrency) {
                this.openRecurringDeletionWizard(record.resId, userAttendeeId);
            } else if (partnerIds.length === 1 && partnerIds[0] === user.partnerId) {
                super.onDeleteSelectedRecords(...arguments);
            } else {
                await this.orm.call("calendar.event", "action_unlink_event", [
                    record.resIds,
                    userAttendeeId,
                ])
                .then((action) => {
                    if (action && action.context) {
                        this.actionService.doAction(action);
                    } else {
                        location.reload();
                    }
                });
            }
        } else {
            const declinedAttendeeIds = [];
            const deletedEventIds = [];
            for (const userAttendeeDetails of userAttendeesDetails) {
                if (userAttendeeDetails.is_organizer) {
                    deletedEventIds.push(userAttendeeDetails.event_id);
                } else {
                    declinedAttendeeIds.push(userAttendeeDetails.attendee_id);
                }
            }
            if (declinedAttendeeIds){
                this.orm.call("calendar.attendee", "do_decline", [declinedAttendeeIds]);
            }
            if (deletedEventIds){
                this.orm.call("calendar.event", "action_unlink_events", [deletedEventIds]);
            }
        }
    }

    async deleteRecords(records) {
        const userAttendeesDetails = await this.orm.call("res.partner", "get_attendee_detail", [
            user.partnerId,
            selectedRecords.map((record) => record.resId),
        ]);
        const declinedAttendeeIds = [];
        const deletedEventIds = [];
        for (const userAttendeeDetails of userAttendeesDetails) {
            if (userAttendeeDetails.is_organizer) {
                deletedEventIds.push(userAttendeeDetails.event_id);
            } else {
                declinedAttendeeIds.push(userAttendeeDetails.attendee_id);
            }
        }
        if (declinedAttendeeIds){
            this.orm.call("calendar.attendee", "do_decline", [declinedAttendeeIds]);
        }
        if (deletedEventIds){
            this.orm.call("calendar.event", "action_unlink_events", [deletedEventIds]);
        }
    }

    deleteConfirmationDialogProps(records) {
        return {
            ...super.deleteConfirmationDialogProps(records),
            body: "This is a body test",
            confirm: deleteRecords,
            confirmLabel: "This is a great test"
        };
    }
}
