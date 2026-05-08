import { ask, makeAwaitable } from "@point_of_sale/app/utils/make_awaitable_dialog";
import { EcpayInfoPopup } from "@l10n_tw_edi_ecpay_pos/app/components/popups/ecpay_info_popup";
import { InvoiceButton } from "@point_of_sale/app/screens/ticket_screen/invoice_button/invoice_button";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(InvoiceButton.prototype, {
    async writeToOrder(order, data = {}) {
        const updates = {
            l10n_tw_edi_is_print: data.l10n_tw_edi_is_print ?? false,
            l10n_tw_edi_love_code: data.l10n_tw_edi_love_code ?? false,
            l10n_tw_edi_carrier_type: data.l10n_tw_edi_carrier_type ?? false,
            l10n_tw_edi_carrier_number: data.l10n_tw_edi_carrier_number ?? false,
            l10n_tw_edi_carrier_number_2: data.l10n_tw_edi_carrier_number_2 ?? false,
        };
        Object.assign(order, updates);
        await this.pos.data.ormWrite("pos.order", [order.id], updates);
    },

    async onWillInvoiceOrder(order, newPartner) {
        let isConfirm = await super.onWillInvoiceOrder(order, newPartner);
        if (
            this.pos.company.country_id?.code === "TW" &&
            this.pos.config.is_ecpay_enabled &&
            newPartner &&
            !order.isToInvoice() &&
            !order.getOrderlines().some((line) => line.refunded_orderline_id) &&
            !order.l10n_tw_edi_is_b2b
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
                return false;
            }

            if (extraEcpayInfo) {
                const payload = await makeAwaitable(this.dialog, EcpayInfoPopup);
                if (payload) {
                    await this.writeToOrder(order, {
                        l10n_tw_edi_love_code: payload.loveCode,
                        l10n_tw_edi_carrier_type: payload.carrierType,
                        l10n_tw_edi_carrier_number: payload.carrierNumber,
                        l10n_tw_edi_carrier_number_2: payload.carrierNumber2,
                    });
                }
                isConfirm &= Boolean(payload);
            } else {
                await this.writeToOrder(order, { l10n_tw_edi_is_print: true });
            }
        }
        return isConfirm;
    },
});
