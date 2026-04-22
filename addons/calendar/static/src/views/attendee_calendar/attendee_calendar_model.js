import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { Domain } from "@web/core/domain";
import { askRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";

export class AttendeeCalendarModel extends CalendarModel {
    static services = [...CalendarModel.services, "dialog", "orm"];

    setup(params, services) {
        super.setup(...arguments);
        this.action = useService("action");
        this.dialog = services.dialog;
        this.rpc = rpc;
    }

    /**
     * @override
     */
    async load() {
        const res = await super.load(...arguments);
        if (!this._loaded) {
            const [credentialStatus, syncStatus, syncEmail, defaultDuration] = await Promise.all([
                rpc("/calendar/check_credentials"),
                this.orm.call("res.users", "check_synchronization_status", [[user.userId]]),
                this.orm.call("res.users", "get_calendar_email", [[user.userId]]),
                this.orm.call("calendar.event", "get_default_duration"),
            ]);
            this.syncStatus = syncStatus;
            this.credentialStatus = credentialStatus;
            this.defaultDuration = defaultDuration;
            this.syncEmail = syncEmail;
            this._loaded = true;
        }
        return res;
    }

    get attendees() {
        return this.data.attendees;
    }

    /**
     * @override
     *
     * Upon updating a record with recurrence, we need to ask how it will affect recurrent events.
     */
    async updateRecord(record) {
        const rec = this.records[record.id];
        if (rec.rawRecord.recurrency) {
            const recurrenceUpdate = await askRecurrenceUpdatePolicy(this.dialog);
            if (!recurrenceUpdate) {
                return this.notify();
            }
            record.recurrenceUpdate = recurrenceUpdate;
        }
        return await super.updateRecord(...arguments);
    }

    /**
     * @override
     */
    buildRawRecord(partialRecord, options = {}) {
        const result = super.buildRawRecord(partialRecord, {
            ...options,
            duration_hour: this.defaultDuration,
        });
        if (partialRecord.recurrenceUpdate) {
            result.recurrence_update = partialRecord.recurrenceUpdate;
        }
        return result;
    }

    /**
     * Load the filter section and add both 'user' and 'everybody' filters to the context.
     * @override
     */
    async loadFilterSection(fieldName, filterInfo, previousSection) {
        // Load calendar ids to which will be used during domain computation
        if (!this._loaded) {
            const userData = await this.orm.read("res.users", [user.userId], ["calendar_ids"])
            this.calendarIds = userData[0]?.calendar_ids
        }
        const result = await super.loadFilterSection(fieldName, filterInfo, previousSection);
        if (result?.fieldName === "calendar_id") {
            result?.filters?.map(f => {
                if (f.isPrimary) {
                    // reuse existing canRemove field on parent component
                    f['canRemove'] = false
                }
            })
        }
        if (result?.fieldName === "partner_ids") {
            if (result?.filters) {
                user.updateContext({
                    calendar_filters: {
                        all: result?.filters?.find((f) => f?.type === "all")?.active ?? false,
                        user: result?.filters?.find((f) => f?.type === "user")?.active ?? false,
                    },
                });
            }
            result.filters = result?.filters?.filter(f => f?.type !== "user");
        }
        return result;
    }

    /**
     * @ override
     */
    computeFiltersDomain(data) {
        const partner_filters = data.filterSections['partner_ids']?.filters || [];
        const activePartnerIds = partner_filters.filter(f => f.active).map(f => f.value) ?? [];
        const calendar_filters = data.filterSections['calendar_id']?.filters || [];
        const activeCalendarIds = calendar_filters.filter(f => f.active).map(f => f.value) ?? [];
        const primaryCalendarFilter = calendar_filters.find(f => f.isPrimary);
        const includesPrimaryCalendar = primaryCalendarFilter?.active ?? false;
        const filterDomains = [[["calendar_id", "in", activeCalendarIds]]];

        // Extend the partner filters to also check for organizers, not just attendees.
        if (activePartnerIds.length) {
            filterDomains.push([
                "|",
                    ["partner_ids", "in", activePartnerIds],
                    ["partner_id", "in", activePartnerIds],
            ]);
        }
        // If the primary calendar is checked, include events the user
        // is attending which are not in any of their calendars.
        if (includesPrimaryCalendar) {
            filterDomains.push([
            "&",
                "|",
                    ["partner_ids", "in", [user.partnerId]],
                    ["partner_id", "=", user.partnerId],
                ["calendar_id", "not in", this.calendarIds],
            ]);
        }
        return Domain.or(filterDomains).toList();
    }

    /**
     * @override
     */
    async updateData(data) {
        await super.updateData(...arguments);
        await this.updateAttendeeData(data);
    }

    /**
     * Split the events to display an event for each attendee with the correct status.
     * If the all filter is activated, we don't display an event for each attendee and keep
     * the previous behavior to display a single event.
     */
    async updateAttendeeData(data) {
        const attendeeFilters = data.filterSections.partner_ids;
        let isEveryoneFilterActive = false;
        let attendeeIds = [];
        const eventIds = Object.keys(data.records).map((id) => Number.parseInt(id));
        if (attendeeFilters) {
            const allFilter = attendeeFilters.filters.find((filter) => filter.type === "all");
            isEveryoneFilterActive = (allFilter && allFilter.active) || false;
            attendeeIds = attendeeFilters.filters
                .filter((filter) => filter.type !== "all" && filter.value)
                .map((filter) => filter.value);
        }
        data.attendees = await this.orm.call("res.partner", "get_attendee_detail", [
            attendeeIds,
            eventIds,
        ]);
        const currentPartnerId = user.partnerId;
        if (!isEveryoneFilterActive && attendeeFilters) {
            const activeAttendeeIds = new Set(
                attendeeFilters.filters
                    .filter((filter) => filter.type !== "all" && filter.value && filter.active)
                    .map((filter) => filter.value)
            );
            // Duplicate records per attendee
            const newRecords = {};
            let duplicatedRecordIdx = -1;
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                const attendees = eventData.partner_id
                    ? [...new Set([...eventData.partner_ids, eventData.partner_id[0]])]
                    : eventData.partner_ids;
                let duplicatedRecords = 0;
                for (const attendee of attendees) {
                    if (!activeAttendeeIds.has(attendee)) {
                        continue;
                    }
                    // Records will share the same rawRecord.
                    const record = { ...event };
                    const attendeeInfo = data.attendees.find(
                        (a) => a.id === attendee && a.event_id === event.id
                    );
                    record.attendeeId = attendee;

                    if (attendee !== user.partnerId) {
                        // Colors are linked to the user's calendars, but in this case we want it linked to attendeeId
                        record.colorIndex = attendee;
                    }
                    if (attendeeInfo) {
                        record.attendeeStatus = attendeeInfo.status;
                        record.isAlone = attendeeInfo.is_alone;
                        record.isCurrentPartner = attendeeInfo.id === currentPartnerId;
                        record.calendarAttendeeId = attendeeInfo.attendee_id;
                    }
                    const recordId = duplicatedRecords ? duplicatedRecordIdx-- : record.id;
                    // Index in the records
                    record._recordId = recordId;
                    newRecords[recordId] = record;
                    duplicatedRecords++;
                }
                // Events added with calendar filters need to be included in the data as well.
                if (duplicatedRecords === 0) {
                    newRecords[event.id] = event;
                }
            }
            data.records = newRecords;
        } else {
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                event.attendeeId = eventData.partner_id && eventData.partner_id[0];
                const attendeeInfo = data.attendees.find(
                    (a) => a.id === currentPartnerId && a.event_id === event.id
                );
                if (attendeeInfo) {
                    event.isAlone = attendeeInfo.is_alone;
                    event.calendarAttendeeId = attendeeInfo.attendee_id;
                }
            }
        }
    }

    /**
     * Archives a record, ask for the recurrence update policy in case of recurrent event.
     */
    async archiveRecord(record) {
        let recurrenceUpdate = false;
        if (record.rawRecord.recurrency) {
            recurrenceUpdate = await askRecurrenceUpdatePolicy(this.dialog);
            if (!recurrenceUpdate) {
                return;
            }
        } else {
            const confirm = await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Bye-bye, record!"),
                    body: deleteConfirmationMessage,
                    confirm: resolve.bind(null, true),
                    confirmLabel: _t("Delete"),
                    confirmClass: "btn-danger",
                    cancel: () => resolve.bind(null, false),
                    cancelLabel: _t("No, keep it"),
                });
            });
            if (!confirm) {
                return;
            }
        }
        await this._archiveRecord(record.id, recurrenceUpdate);
    }

    async _archiveRecord(id, recurrenceUpdate) {
        if (!recurrenceUpdate && recurrenceUpdate !== "self_only") {
            await this.orm.call(this.resModel, "action_archive", [[id]]);
        } else {
            await this.orm.call(this.resModel, "action_mass_archive", [[id], recurrenceUpdate]);
        }
        await this.load();
    }

    normalizeRecord(rawRecord) {
        const normalizedRecord = super.normalizeRecord(rawRecord);
        if (rawRecord.effective_privacy === "private") {
            normalizedRecord.titleIcon = "fa fa-lock";
        }
        if (rawRecord['calendar_color']) {
            normalizedRecord.colorIndex = rawRecord['calendar_color'];
        }
        return normalizedRecord;
    }

    /**
     * @override
     */
    makeFilterRecord(filterInfo, previousFilter, rawRecord) {
        let filterRecord = super.makeFilterRecord(...arguments);
        // update the filter color
        const { colorFieldName } = filterInfo;
        const colorValue = rawRecord[colorFieldName]
        if (colorValue) {
            filterRecord.colorIndex = colorValue;
        } else if (rawRecord.partner_id) {
            filterRecord.colorIndex = rawRecord.partner_id[0];
        }
        // Add is_primary to calendar filters
        if (rawRecord['is_primary']) {
            filterRecord['isPrimary'] = rawRecord['is_primary'];
        }
        return filterRecord;
    }

    /**
     * @override - fetch the is_primary field for calendar filters
     */
    fetchFilters(resModel, fieldNames) {
        return super.fetchFilters(resModel, resModel === 'calendar.calendar.filter' ?
            [...fieldNames, 'is_primary'] : fieldNames);

    }
}
