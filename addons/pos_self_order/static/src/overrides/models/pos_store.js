import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.data.connectWebSocket(
            "SELF_ORDER_PRINT_REQ",
            async ({ order_id }) => await this._handleSelfOrderPrintReq(order_id)
        );
    },
    async _handleSelfOrderPrintReq(orderId) {
        // Wait for the order to be available in the local store.
        // The SYNCHRONISATION notification delivers the order data asynchronously,
        // so it may arrive slightly after this notification.
        let order = null;
        for (let attempt = 0; attempt < 10; attempt++) {
            order = this.models["pos.order"].get(orderId);
            if (order) {
                break;
            }
            await new Promise((resolve) => setTimeout(resolve, 500));
        }

        if (!order) {
            // Fallback: trigger a full sync to fetch the order
            try {
                await this.syncAllOrders();
                order = this.models["pos.order"].get(orderId);
            } catch {
                return;
            }
        }

        if (order && order.state === "draft") {
            await this.sendOrderInPreparation(order);
        }
    },
    async getServerOrders() {
        if (this.session._self_ordering) {
            await this.data.loadServerOrders([
                ["company_id", "=", this.config.company_id.id],
                ["state", "=", "draft"],
                ["source", "=", "kiosk"],
            ]);
        }

        return await super.getServerOrders(...arguments);
    },
    async redirectToQrForm() {
        const user_data = await this.data.call("pos.config", "get_pos_qr_order_data", [
            this.config.id,
        ]);
        return await this.action.doAction({
            type: "ir.actions.client",
            tag: "pos_qr_stands",
            params: { data: user_data },
        });
    },
});
