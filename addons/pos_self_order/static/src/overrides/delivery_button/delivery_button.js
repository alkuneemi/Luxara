import { useEffect, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { DeliveryButton } from "@point_of_sale/app/components/delivery_button/delivery_button";
import { SnoozeDialog } from "@point_of_sale/app/components/popups/product_info_popup/snooze_dialog/snooze_dialog";

patch(DeliveryButton.prototype, {
    setup() {
        super.setup();
        this.state = useState({
            countdown: "",
            activeSelfSnoozed: this.activeSelfSnooze,
        });

        useEffect(
            () => {
                if (this.state.activeSelfSnoozed) {
                    [this.state.countdown, this.state.activeSelfSnoozed] = this.pos.updateCountdown(
                        this.state.activeSelfSnoozed
                    );
                    const interval = setInterval(() => {
                        [this.state.countdown, this.state.activeSelfSnoozed] =
                            this.pos.updateCountdown(this.state.activeSelfSnoozed);
                    }, 1000);
                    return () => {
                        clearInterval(interval);
                    };
                }
            },
            () => [this.state.activeSelfSnoozed]
        );
    },
    get activeSelfSnooze() {
        return this.pos.snoozedProductTracker.state.activeSnoozes.find(
            (record) => record.is_self_snoozed
        );
    },
    get ongoingOrders() {
        return this.pos.models["pos.order"].filter(
            (o) => ["mobile", "kiosk"].includes(o.source) && o.state == "draft"
        ).length;
    },
    async snoozeSelfOrdering() {
        // If already snoozed, unsnooze self-order service.
        if (this.state.activeSelfSnoozed) {
            this.pos.openSnoozeDialog({
                snoozedItem: this.state.activeSelfSnoozed,
                onReset: () => {
                    this.state.activeSelfSnoozed = undefined;
                    this.state.countdown = "";
                },
            });
            return;
        }
        // Snooze self-order service for a specific time.
        this.pos.dialog.add(SnoozeDialog, {
            name: "Self Order Services",
            onSave: async (hours) => {
                const snoozePayload = this.pos.prepareSnoozePayload(undefined, hours, {
                    isSelfSnoozed: true,
                });
                this.state.activeSelfSnoozed = (
                    await this.pos.data.create("pos.snooze", [snoozePayload])
                )[0];
                await this.pos.data.call("pos.config", "update_self_order", [this.pos.config.id]);
            },
        });
    },
});
