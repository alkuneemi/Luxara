import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import {
    BadgesSelectionField,
    badgesSelectionField,
} from "@web/views/fields/badges_selection/badges_selection_field";

export class HrHolidaysBadgeSelectionWithFilterField extends BadgesSelectionField {
    get options() {
        const { name, record } = this.props;
        const forceFullDuration = record.context?.force_full_duration;
        if (forceFullDuration && name === "request_duration") {
            return record.fields[name].selection.filter(([value]) => value === "full");
        }
        return super.options;
    }
}

export const hrHolidaysBadgeSelectionFieldWithFilter = {
    ...badgesSelectionField,
    component: HrHolidaysBadgeSelectionWithFilterField,
    displayName: _t("Badges for Selection With Filter (Full Day)"),
};

registry.category("fields").add("selection_badge_with_filter_full_day", hrHolidaysBadgeSelectionFieldWithFilter);
