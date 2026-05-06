import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class DeliveryButton extends Component {
    static template = "point_of_sale.DeliveryButton";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
    }

    // Shared methods used by both Self Order and Urban Piper
    goToOrders(serviceName, filter = "ONGOING", searchTerm = "") {
        const props = this.getTicketScreenProps(serviceName, filter, searchTerm);
        return this.redirectTicketScreen(props);
    }
    getTicketScreenProps(serviceName, filter = "ONGOING", searchTerm = "") {
        return {
            stateOverride: {
                search: {
                    fieldName: serviceName,
                    searchTerm: searchTerm,
                },
                filter: filter,
            },
        };
    }
    redirectTicketScreen(props) {
        if (this.pos.router.state.current == "TicketScreen") {
            this.ui.block();
            this.pos.ticket_screen_mobile_pane = "left";
            const nextPage = this.pos.defaultPage;
            this.pos.navigate(nextPage.page, nextPage.params);
            setTimeout(() => {
                this.pos.navigate("TicketScreen", props);
                this.ui.unblock();
            }, 300);
            return;
        }
        this.pos.navigate("TicketScreen", props);
    }
}
