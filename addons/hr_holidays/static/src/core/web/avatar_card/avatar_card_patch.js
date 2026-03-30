import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart, useState } from "@odoo/owl";

/** @type {AvatarCard} */
const avatarCardTimeOffPatch = {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            leaveSummary: null,
        });

        onWillStart(async () => {
            const allowedModels = ["hr.employee", "hr.employee.public"];
            if (this.props.id && allowedModels.includes(this.props.model)) {
                await this._fetchTimeOffSummary(this.props.id);
            }
        });
    },

    async _fetchTimeOffSummary(employeeId) {
        const summary = await this.orm.call("hr.employee", "get_avatar_leave_summary", [
            employeeId,
        ]);
        this.state.leaveSummary = summary;
    },

    async onTimeOffClick() {
        if (!this.props.id) {
            return;
        }
        const action = await this.orm.call("hr.employee", "action_time_off_dashboard", [
            [this.props.id],
        ]);
        if (action) {
            await this.actionService.doAction(action);
        }
    },

    /** @override */
    get hasFooter() {
        return !!this.state.leaveSummary || super.hasFooter;
    },
};

export const unpatchAvatarCard = patch(AvatarCard.prototype, avatarCardTimeOffPatch);
