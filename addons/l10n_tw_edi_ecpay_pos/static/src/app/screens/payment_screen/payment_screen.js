import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/app/components/popups/ecpay_info_popup";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            this.currentOrder.getPartner()
        ) {
            this.currentOrder.setToInvoice(true);
            this.currentOrder.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
        }
    },

    // @override
    async toggleIsToInvoice() {
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            this.currentOrder.getPartner() &&
            !this.currentOrder.isToInvoice() &&
            !this.currentOrder.getOrderlines().some((line) => line.refunded_orderline_id) &&
            !this.currentOrder.l10n_tw_edi_is_b2b
        ) {
            let dismiss = false;
            const extraEcpayInfo = await ask(this.dialog, {
                title: _t("Ecpay Invoicing Confirmation"),
                body: _t("Store in Carrier or Donate?"),
                confirmLabel: _t("Yes"),
                cancelLabel: _t("No"),
                dismiss: () => {
                    dismiss = true;
                },
            });

            if (dismiss) {
                this.currentOrder.setToInvoice(false);
                this.currentOrder.setEcpayInvoiceInfo({});
                return;
            }

            if (extraEcpayInfo) {
                const payload = await makeAwaitable(this.dialog, EcpayInfoPopup);

                if (!payload) {
                    this.currentOrder.setToInvoice(false);
                    this.currentOrder.setEcpayInvoiceInfo({});
                    return;
                }

                this.currentOrder.setEcpayInvoiceInfo({
                    l10n_tw_edi_love_code: payload.loveCode,
                    l10n_tw_edi_carrier_type: payload.carrierType,
                    l10n_tw_edi_carrier_number: payload.carrierNumber,
                    l10n_tw_edi_carrier_number_2: payload.carrierNumber2,
                });
            } else {
                this.currentOrder.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
            }
        }
        super.toggleIsToInvoice(...arguments);
    },
});
