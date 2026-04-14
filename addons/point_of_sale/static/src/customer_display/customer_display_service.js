import { registry } from "@web/core/registry";
import { reactive } from "@web/owl2/utils";
import { session } from "@web/session";
import { getOnNotified, uuidv4 } from "@point_of_sale/utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

export const CONSOLE_COLOR = "#F5B427";

export class CustomerDisplayService {
    constructor(...args) {
        this.setup(...args);
    }

    async setup(env, { orm, bus_service }) {
        this.env = env;
        this.orm = orm;
        this.bus = bus_service;
        this.data = reactive({});

        // Fallback communication channel used when WebRTC is unavailable (e.g., network loss).
        // NOTE: Works only between contexts within the same browser (tabs/windows sharing the same origin).
        this.channel = new BroadcastChannel("UPDATE_CUSTOMER_DISPLAY");
    }

    async initSender(identifier, models, GeneratePrinterData) {
        this.models = models;
        this.GeneratePrinterData = GeneratePrinterData;
        this.identifier = identifier;
    }

    /**
     * Hook to extend the payload sent to the customer display.
     *
     * Override this method to customize the data derived from the order before
     * it is sent (e.g., add extra fields, metadata, or UI-specific flags).
     *
     * @param {Order} order - The current order instance.
     * @returns {Object} Data payload for the customer display.
     */
    _buildDisplayPayload(order) {
        const generator = new this.GeneratePrinterData({
            models: this.models,
            order,
        });

        const orderData = generator.generateReceiptData();
        const selectedUuid = order.uiState?.selected_orderline_uuid;
        const formatCurrency = this.env.utils.formatCurrency;

        orderData.lines = orderData.lines.map((lineData, index) => {
            const lineRecord = order.lines[index];
            return {
                ...lineData,
                isSelected: lineData.uuid === selectedUuid,
                displayPriceNoDiscount: formatCurrency(lineRecord?.displayPriceNoDiscount || 0),
            };
        });

        const qrPaymentData = order.getSelectedPaymentline()?.getQrPopupProps(true);
        if (qrPaymentData?.amount) {
            qrPaymentData.amount = formatCurrency(qrPaymentData.amount);
        }

        return {
            ...orderData,
            qrPaymentData,
            payloadHash: uuidv4(),
            displayScreenSaver: false,
            change: formatCurrency(order.remainingDue),
        };
    }

    sendOrder(order) {
        if (!(this.models && this.GeneratePrinterData && order && this.env.utils?.formatCurrency)) {
            return;
        }
        const orderPayload = this._buildDisplayPayload(order);
        this.send(orderPayload);
    }

    send(payload) {
        const payloadStr = JSON.stringify(payload);
        this.orm
            .call("pos.config", "update_customer_display", [
                [odoo.pos_config_id],
                payloadStr,
                this.identifier,
            ])
            .catch((error) => {
                logPosMessage(
                    "CustomerDisplay",
                    "dispatch",
                    "Failed to update customer display",
                    CONSOLE_COLOR,
                    [error]
                );
            });
        this.channel.postMessage(payloadStr);
    }

    async initReceiver(identifier) {
        getOnNotified(this.bus, session.access_token)(
            `UPDATE_CUSTOMER_DISPLAY-${identifier}`,
            (payload) => this._onDataReceived(payload)
        );

        this.channel.onmessage = (event) => this._onDataReceived(event.data);
    }

    _onDataReceived(rawData) {
        if (typeof rawData !== "string") {
            return;
        }
        let parsedData;
        try {
            parsedData = JSON.parse(rawData);
        } catch (error) {
            logPosMessage(
                "CustomerDisplayService",
                "onDataReceived",
                "Failed to parse WebRTC message",
                CONSOLE_COLOR,
                [error]
            );
            return;
        }

        if (!parsedData || parsedData.payloadHash === this.data.payloadHash) {
            return;
        }
        Object.assign(this.data, parsedData);
    }
}

export const customerDisplayService = {
    dependencies: ["bus_service", "orm"],
    async start(env, services) {
        return new CustomerDisplayService(env, services);
    },
};

registry.category("services").add("customer_display_service", customerDisplayService);
