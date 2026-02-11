import { browser } from "@web/core/browser/browser";
import {
    CardRenderer,
    getColorIndex,
    getFormattedRecord,
    getImageSrcFromRecordInfo,
    getRawValue,
} from "@web/views/card/card_renderer";
import { TOUCH_SELECTION_THRESHOLD } from "@web/views/utils";

// Re-export for backwards compatibility
export { getColorIndex, getFormattedRecord, getImageSrcFromRecordInfo, getRawValue };

// These classes determine whether a click on a record should open it.
export const CANCEL_GLOBAL_CLICK = ["a", ".dropdown", ".oe_kanban_action", "[data-bs-toggle]"].join(
    ","
);

export class KanbanRecord extends CardRenderer {
    static template = "web.KanbanRecord";
    static props = [
        ...CardRenderer.props,
        "canResequence?",
        "forceGlobalClick?",
        "getSelection?",
        "groupByField?",
        "selectionAvailable?",
        "progressBarState?",
        "toggleSelection?",
    ];
    static defaultProps = {
        ...CardRenderer.defaultProps,
        getSelection: () => [],
        selectionAvailable: false,
        toggleSelection: () => {},
    };

    static CANCEL_GLOBAL_CLICK = CANCEL_GLOBAL_CLICK;
    static PROGRESS_COLOR_PREFIX = "oe_kanban_card_"; // TODO AAB: rename
    static HIGHLIGHT_COLOR_PREFIX = "o_kanban_color_"; // TODO AAB: rename

    setup() {
        super.setup();

        this.LONG_TOUCH_THRESHOLD = this.props.canResequence ? 600 : TOUCH_SELECTION_THRESHOLD;
        this.longTouchTimer = null;
        this.touchStartMs = 0;
    }

    get renderingContext() {
        return {
            ...super.renderingContext,
            selection_mode: this.props.forceGlobalClick,
        };
    }

    createWidget(props) {
        super.createWidget(props);
        if (this.props.groupByField?.type === "many2many") {
            this.dataState.widget.deletable = false;
        }
    }

    getRecordClasses() {
        const classes = super.getRecordClasses().split(" ");

        classes.push("o_kanban_record");

        const { archInfo, canResequence, forceGlobalClick, record, progressBarState } = this.props;
        if (canResequence) {
            classes.push("o_draggable");
        }
        if (forceGlobalClick || archInfo.openAction || archInfo.canOpenRecords) {
            classes.push("cursor-pointer");
        }
        if (progressBarState) {
            const { fieldName, colors } = progressBarState.progressAttributes;
            const value = record.data[fieldName];
            const color = colors[value];
            if (color) {
                classes.push(`${this.constructor.PROGRESS_COLOR_PREFIX}${color}`);
            }
        }
        if (archInfo.cardColorField) {
            const value = record.data[archInfo.cardColorField];
            classes.push(`${this.constructor.HIGHLIGHT_COLOR_PREFIX}${getColorIndex(value)}`);
        }
        if (!this.props.groupByField) {
            classes.push("flex-grow-1 flex-md-shrink-1 flex-shrink-0");
        }
        if (this.props.selectionAvailable) {
            classes.push("o_record_selection_available");
        }
        if (this.props.record.selected) {
            classes.push("o_record_selected");
        }
        if (
            this.offlineService.offline &&
            !this.props.record.model.useSampleModel &&
            !this.offlineService.isAvailableOffline(this.env.config.actionId, "form", record.resId)
        ) {
            classes.push("o_disabled_offline");
        }
        return classes.join(" ");
    }

    /**
     * @override
     */
    triggerAction(params) {
        const { archiveRecord, record } = this.props;
        switch (params.type) {
            case "archive":
                return archiveRecord(record, true);
            case "unarchive":
                return archiveRecord(record, false);
        }
        return super.triggerAction(params);
    }

    /**
     * @param {MouseEvent} ev
     */
    onGlobalClick(ev, newWindow) {
        if (ev.target.closest(this.constructor.CANCEL_GLOBAL_CLICK)) {
            return;
        }
        if (this.props.getSelection().length > 0 || ev.altKey) {
            ev.stopPropagation();
            ev.preventDefault();
            this.rootRef.el.focus();
            this.props.toggleSelection(this.props.record, ev.shiftKey);
            return;
        }
        const { archInfo, forceGlobalClick, openRecord, record } = this.props;
        if (!forceGlobalClick && archInfo.openAction) {
            this.action.doActionButton(
                {
                    name: archInfo.openAction.action,
                    type: archInfo.openAction.type,
                    resModel: record.resModel,
                    resId: record.resId,
                    resIds: record.resIds,
                    context: record.context,
                    onClose: async () => {
                        await record.model.root.load();
                    },
                },
                {
                    newWindow,
                }
            );
        } else if (forceGlobalClick || this.props.archInfo.canOpenRecords) {
            openRecord(record, { newWindow });
        }
    }

    resetLongTouchTimer() {
        if (this.longTouchTimer) {
            browser.clearTimeout(this.longTouchTimer);
            this.longTouchTimer = null;
        }
    }

    onTouchStart() {
        this.touchStartMs = Date.now();
        if (this.longTouchTimer === null) {
            this.longTouchTimer = browser.setTimeout(() => {
                this.props.record.toggleSelection(true);
                this.resetLongTouchTimer();
            }, this.LONG_TOUCH_THRESHOLD);
        }
    }

    onTouchEnd() {
        const elapsedTime = Date.now() - this.touchStartMs;
        if (elapsedTime < this.LONG_TOUCH_THRESHOLD) {
            this.resetLongTouchTimer();
        }
    }

    onTouchMoveOrCancel() {
        this.resetLongTouchTimer();
    }
}
