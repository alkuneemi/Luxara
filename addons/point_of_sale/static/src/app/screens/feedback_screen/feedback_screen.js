import { useLayoutEffect, useState } from "@web/owl2/utils";
import { registry } from "@web/core/registry";
import { Component, onWillUnmount } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { useErrorHandlers } from "@point_of_sale/app/hooks/hooks";
import { useRouterParamsChecker } from "@point_of_sale/app/hooks/pos_router_hook";
import { PrintPopup } from "@point_of_sale/app/components/popups/print_popup/print_popup";
import { SendReceiptPopup } from "@point_of_sale/app/components/popups/send_receipt_popup/send_receipt_popup";
import { FeedbackPaymentSummary } from "@point_of_sale/app/components/feedback_payment_summary/feedback_payment_summary";

export class FeedbackScreen extends Component {
    static template = "point_of_sale.FeedbackScreen";
    static storeOnOrder = false;
    static components = { FeedbackPaymentSummary };
    static props = {
        orderUuid: String,
        waitFor: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        useRouterParamsChecker();
        useErrorHandlers();
        this.notification = useService("notification");
        this.ui = useService("ui");
        this.dialog = useService("dialog");
        this.state = useState({
            loading: true,
            timeout: false,
        });

        useLayoutEffect(
            () => {
                const waiter = async () => {
                    try {
                        if (this.props.waitFor) {
                            await this.props.waitFor;
                        }
                    } finally {
                        await this._afterWaitFinished();
                    }
                };

                waiter();
            },
            () => []
        );

        onWillUnmount(() => {
            clearTimeout(this.state.timeout);
        });
    }

    async _afterWaitFinished() {
        this.state.loading = false;

        if (this.isAutoSkip && !this.ignoreTimeout) {
            this.state.timeout = setTimeout(() => {
                this.pos.orderDone(this.currentOrder);
            }, this.pos.feedbackScreenAutoSkipDelay);
        }
    }

    get isAutoSkip() {
        return (
            this.pos.config.iface_print_auto && this.currentOrder.payment_ids[0]?.payment_method_id
        );
    }

    get currentOrder() {
        return this.pos.models["pos.order"].getBy("uuid", this.props.orderUuid);
    }

    onClick(buttonClicked = false) {
        if (!this.isAutoSkip || buttonClicked) {
            if (this.state.loading) {
                this.notification.add(
                    _t("A request is still being processed in the background. Please wait."),
                    {
                        type: "warning",
                    }
                );
                return;
            }
            this.goNext();
        } else {
            this.stopAutomaticSkip();
        }
    }

    stopAutomaticSkip() {
        if (!this.isAutoSkip) {
            return;
        }
        if (this.state.timeout) {
            clearTimeout(this.state.timeout);
            this.state.timeout = false;
        } else {
            this.ignoreTimeout = true;
        }
    }

    goNext() {
        this.pos.orderDone(this.currentOrder);
    }

    get canSendReceipt() {
        return true;
    }

    get canPrintReceipt() {
        return true;
    }

    clickPrint() {
        this.stopAutomaticSkip();
        this.dialog.add(PrintPopup, {
            order: this.currentOrder,
        });
    }

    clickSend() {
        this.stopAutomaticSkip();
        if (this.canSendReceipt) {
            this.dialog.add(SendReceiptPopup, {
                order: this.currentOrder,
            });
        }
    }

    clickEditPayment() {
        this.stopAutomaticSkip();
        this.pos.editPayment(this.currentOrder);
    }
}

registry.category("pos_pages").add("FeedbackScreen", {
    name: "FeedbackScreen",
    component: FeedbackScreen,
    route: `/pos/ui/${odoo.pos_config_id}/resume/{string:orderUuid}`,
    params: {},
});
