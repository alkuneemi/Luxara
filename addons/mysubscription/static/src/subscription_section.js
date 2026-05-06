import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";

function capitalize(string) {
    if (string.length > 1) {
        return string.charAt(0).toUpperCase() + string.slice(1);
    } else {
        return string;
    }
}

export class SubscriptionSection extends Component {
    static template = "mysubscription.SubscriptionSection";
    static props;

    setup() {
        this.dashboardState = useState(this.env.dashboardState);
    }

    get expirationDate() {
        if (this.dashboardState.expirationDate) {
            return _t(`Expires on ${this.dashboardState.expirationDate}`);
        }
        else if (this.dashboardState.enterpriseCode) {
            return _t("Pending Validation");
        }
        else {
            return _t(`Running on ${capitalize(_t(this.dashboardState.expirationReason))}`);
        }
    }
}

