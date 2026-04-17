import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class IapContainer extends Component {
    static template = "mysubscription.IapContainer";
    static props = {
        account: { type: Object },
    }

    setup() {
        this.actionService = useService("action");
        this.state = useState({ isHovered: null });
    }

    openSettings() {
        const actionDict = this.props.account.action;
        if (!actionDict.views) {
            actionDict.views = [[false, "form"]];
        }
        this.actionService.doAction(actionDict);
    }

    get name() {
        return this.props.account.name;
    }

    get balance() {
        return this.props.account.balance;
    }

    get creditUrl() {
        return this.props.account.credit_url;
    }

    get imageUrl() {
        const service = this.props.account.service_name;
        const existingIcon = ["sms", "reveal", "snailmail", "partner_autocomplete", "invoice_ocr"];
        if (existingIcon.includes(service)) {
            return `/mysubscription/static/src/img/${service}_icon.png`;
        }
        return "/mysubscription/static/src/img/default_iap_icon.png";
    }

    openTopUp() {
        window.open(this.creditUrl, "_blank");
    }
}

export class IapSection extends Component {
    static template = "mysubscription.IapSection";
    static components = {
        IapContainer,
    };
    static props;

    setup() {
        this.orm = useService("orm");

        onWillStart(async () => {
            this.iapAccounts = await this.loadIap();
            console.log(this.iapAccounts);
        });
    }

    async loadIap() {
        const configData = await this.orm.call(
            "mysubscription.mysubscription",
            "get_iap_data",
            []
        );
        return configData;
    }

}
