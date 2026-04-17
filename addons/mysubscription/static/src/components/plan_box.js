import { Component, useState } from "@odoo/owl";

export class PlanBox extends Component {
    static template = "mysubscription.PlanBox";

    static props = {
        data: { type: Object },
    }

    setup() {
        this.dashboardState = useState(this.env.dashboardState);
    };

    onClickPlan() {
        this.dashboardState.selectedPlan = this.props.data.id;
    }

    get isCurrentPlanSelected() {
        return this.dashboardState.selectedPlan === this.props.data.id;
    }
}
