import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { EcpayCertificateReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_certificate_receipt";
import { EcpayTransactionReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_transaction_receipt";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

const { DateTime } = luxon;

patch(PosStore.prototype, {
    async _getUniformInvoiceData(order) {
        const uniform_inovice = await this.data.call(
            "pos.order",
            "l10n_tw_edi_get_uniform_invoice",
            [order.id, order.name]
        );

        if (uniform_inovice) {
            order.invoice_month = uniform_inovice.invoice_month;
            order.iis_number = uniform_inovice.iis_number;
            order.iis_create_date = DateTime.fromSQL(uniform_inovice.iis_create_date, {
                zone: "utc",
            })
                .toLocal()
                .toFormat("yyyy-MM-dd HH:mm:ss");
            order.iis_random_number = uniform_inovice.iis_random_number;
            order.iis_tax_amount = uniform_inovice.iis_tax_amount;
            order.l10n_tw_edi_invoice_amount = uniform_inovice.l10n_tw_edi_invoice_amount;
            order.iis_identifier = uniform_inovice.iis_identifier;
            order.iis_carrier_type =
                order.l10n_tw_edi_carrier_type === "0" ? "" : uniform_inovice.iis_carrier_type;
            order.iis_carrier_num = uniform_inovice.iis_carrier_num;
            order.iis_category = uniform_inovice.iis_category;
            order.l10n_tw_edi_ecpay_seller_identifier =
                uniform_inovice.l10n_tw_edi_ecpay_seller_identifier;
            order.pos_barcode = uniform_inovice.pos_barcode;
            order.qrcode_left = uniform_inovice.qrcode_left;
            order.qrcode_right = uniform_inovice.qrcode_right;
            order.ecpay_error = uniform_inovice.ecpay_error;
            order.company_logo_exist = uniform_inovice.company_logo_exist;
        }
        if (order.ecpay_error && order.is_invoiced) {
            await this.dialog.add(AlertDialog, {
                title: _t("Submission failed"),
                body:
                    _t("\n Submission to ECPay failed") +
                    uniform_inovice.ecpay_error.replace(/<[^>]*>/g, "") +
                    _t("\n Please correct the issue in the accounting app"),
            });
        }
    },

    async selectPartner() {
        const res = await super.selectPartner();
        const order = this.getOrder();
        const partner = this.getOrder().getPartner();
        if (this.company.country_id?.code === "TW" && this.config.is_ecpay_enabled) {
            if (partner) {
                order.setToInvoice(true);
                order.setEcpayInvoiceInfo({ l10n_tw_edi_is_print: true });
                order.l10n_tw_edi_is_b2b = partner.commercial_partner_id.is_company;
            } else {
                order.setToInvoice(false);
                order.setEcpayInvoiceInfo({});
                order.l10n_tw_edi_is_b2b = false;
            }
        }
        return res;
    },

    async syncAllOrders(options = {}) {
        const result = await super.syncAllOrders(options);
        const order = this.getOrder();
        if (result && result.length && order.isPrintEcpayInvoice) {
            await this._getUniformInvoiceData(order);
        }
        return result;
    },

    async printReceipt({
        basic = false,
        order = this.getOrder(),
        printBillActionTriggered = false,
    } = {}) {
        if (order.isPrintEcpayInvoice && !order.ecpay_error) {
            await this._getUniformInvoiceData(order);
        }
        const result = await super.printReceipt({ basic, order, printBillActionTriggered });
        if (result && order.isPrintEcpayInvoice && !order.ecpay_error) {
            await this.printer.print(
                EcpayCertificateReceipt,
                {
                    order,
                },
                this.printOptions
            );
            await this.printer.print(
                EcpayTransactionReceipt,
                {
                    order,
                },
                this.printOptions
            );
        }
        return result;
    },
});
