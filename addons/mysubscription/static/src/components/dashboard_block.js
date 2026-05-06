import { Component } from "@odoo/owl";

export class DashboardBlock extends Component {
    static template = "mysubscription.DashboardBlock";

    static props = {
        subtitle: { type: String, optional: true },
        slots: { type: Object, optional: true },
    }

    setup() {};
}
