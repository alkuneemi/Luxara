import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.company.country_id?.code === "TW" && this.config.is_ecpay_enabled) {
            if (!this.partner_id && this.config._default_tw_customer_id) {
                this.update({ partner_id: this.config._default_tw_customer_id });
            }
            if (this.partner_id) {
                this.l10n_tw_edi_is_b2b = this.partner_id.commercial_partner_id.is_company;
            }
        }
    },

    setEcpayInvoiceInfo({
        l10n_tw_edi_is_print = false,
        l10n_tw_edi_love_code = false,
        l10n_tw_edi_carrier_type = false,
        l10n_tw_edi_carrier_number = false,
        l10n_tw_edi_carrier_number_2 = false,
    } = {}) {
        this.l10n_tw_edi_is_print = l10n_tw_edi_is_print;
        this.l10n_tw_edi_love_code = l10n_tw_edi_love_code;
        this.l10n_tw_edi_carrier_type = l10n_tw_edi_carrier_type;
        this.l10n_tw_edi_carrier_number = l10n_tw_edi_carrier_number;
        this.l10n_tw_edi_carrier_number_2 = l10n_tw_edi_carrier_number_2;
    },

    get isPrintEcpayInvoice() {
        return (
            this.config.is_ecpay_enabled &&
            this.company.country_id?.code === "TW" &&
            this.isToInvoice() &&
            this.l10n_tw_edi_is_print &&
            !this.l10n_tw_edi_is_b2b &&
            !this.getOrderlines().some((line) => line.refunded_orderline_id)
        );
    },
});
