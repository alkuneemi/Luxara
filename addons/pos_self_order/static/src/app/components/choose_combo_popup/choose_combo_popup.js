import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

export class ChooseComboPopup extends Component {
    static template = "pos_self_order.ChooseComboPopup";
    static components = { Dialog };
    static props = {
        potentialCombos: Object,
        close: Function,
        getPayload: Function,
    };

    setup() {
        this.selfOrder = useSelfOrder();
        this.ui = useService("ui");
    }

    get allCombos() {
        return this.selfOrder.comboSuggestion.getAllComboChoices(this.props.potentialCombos);
    }

    confirm(combo) {
        this.props.getPayload(combo);
        this.props.close();
    }
}
