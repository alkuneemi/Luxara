import { Component, onWillStart, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatCurrency } from "@web/core/currency";
import { renderToMarkup } from "@web/core/utils/render";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { QuantityButtons } from "@sale/js/quantity_buttons/quantity_buttons";

export class ReturnOrderDialog extends Component {
    static components = { Dialog, WarningDialog, QuantityButtons };
    static template = "sale_stock.ReturnOrderDialog";
    static props = {
        saleOrderId: Number,
        accessToken: String,
        close: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.state =  useState({ returnableLines: [], returnReason: null });
        this.url = `/my/orders/${this.props.saleOrderId}/download_return_label`;

        onWillStart(async () => {
            this.content = await this._loadData();
            this.state.returnableLines = this.content.returnable_lines;
            this.formatCurrency = (amount) => formatCurrency(amount, this.content.currency_id);
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _loadData() {
        return rpc("/return/order/content", {
            order_id: this.props.saleOrderId,
            access_token: this.props.accessToken,
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    setQuantity(line, quantity) {
        line.quantity = Math.min(Math.max(quantity, 0), line.remaining_delivered_qty);
        return true;
    }

    onReturnReasonChange(ev) {
        this.state.returnReason = ev.target.value;
    }

    async onContinue() {
        const selectedLines = this.state.returnableLines.filter(line => line.quantity);
        const isSinglePickingWithLabel = (
            selectedLines.length > 0
            && selectedLines.every(
                line => line.picking_id === selectedLines[0].picking_id
            )
            && !!selectedLines[0].shipping_label_url

        );
        let dialogProps = {
            title: _t("Print the return request label."),
            body: renderToMarkup("sale_stock.ReturnLabelBody", {
                companyName: this.content.company_name,
                warehouseAddress: this.content.warehouse_address,
                isSinglePickingWithLabel: isSinglePickingWithLabel,
            }),
            confirmLabel: _t("Download Return Label"),
            confirm: async () => await this._downloadReturnLabel(selectedLines),
            size: "md",
        }
        // Don't display shiping label button for multiple pickings
        if (isSinglePickingWithLabel) {
            dialogProps = {
                ...dialogProps,
                // Used cancel button as downloading shipping label button
                cancelLabel: _t("Download Shipping Label"),
                cancel: () => this._downloadShippingLabel(selectedLines[0].shipping_label_url),
            }
        }
        this.dialog.add(ConfirmationDialog, dialogProps);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _downloadReturnLabel(selectedLines) {
        const pickingDetails = {};
        selectedLines.forEach(line => {
            if (!pickingDetails[line.picking_id]) {
                pickingDetails[line.picking_id] = [];
            }
            pickingDetails[line.picking_id].push([line.product_id, line.quantity]);
        });
        const params = {
            order_id: this.props.saleOrderId,
            access_token: this.props.accessToken,
            picking_details: JSON.stringify(pickingDetails),
            return_reason: this.state.returnReason,
        }
        const query = new URLSearchParams(params).toString();
        window.open(`${ this.url }?${ query }`, "_blank");
        this.props.close();
    }

    _downloadShippingLabel(shipping_label_url) {
        window.open(shipping_label_url, "_blank");
        this.props.close();
    }

}
