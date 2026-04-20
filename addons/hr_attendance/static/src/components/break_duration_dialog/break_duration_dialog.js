import { Component, useRef, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { sprintf } from "@web/core/utils/strings";

export class BreakDurationDialog extends Component {
    static template = "hr_attendance.BreakDurationDialog";
    static components = { Dialog };
    static props = {
        employeeName: { type: String, optional: true },
        defaultMinutes: { type: Number, optional: true },
        maxMinutes: { type: Number, optional: true },
        onConfirm: { type: Function },
        onCancel: { type: Function, optional: true },
        close: { type: Function },
    };

    setup() {
        this.state = useState({
            minutes: this.props.defaultMinutes ?? 0,
        });
        this.durationInputRef = useRef("durationInput");
        this.dialogTitle = _t("Break Duration");
        this.promptText = this.props.employeeName
            ? sprintf(
                  _t("Enter the extra break duration (in minutes) for %s."),
                  this.props.employeeName
              )
            : _t("Enter the extra break duration in minutes.");
    }

    get maxMinutes() {
        if (typeof this.props.maxMinutes !== "number") {
            return null;
        }
        return Math.max(Math.floor(this.props.maxMinutes), 0);
    }

    async confirm(ev) {
        ev.preventDefault();
        const input = this.durationInputRef.el;
        if (input && !input.reportValidity()) {
            return;
        }
        const shouldClose = await this.props.onConfirm(Number(this.state.minutes) || 0);
        if (shouldClose !== false) {
            this.props.close();
        }
    }

    cancel() {
        if (this.props.onCancel) {
            this.props.onCancel();
        }
        this.props.close();
    }
}
