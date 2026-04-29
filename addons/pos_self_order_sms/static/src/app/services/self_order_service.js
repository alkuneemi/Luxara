import { patch } from "@web/core/utils/patch";
import { SelfOrder } from "@pos_self_order/app/services/self_order_service";

patch(SelfOrder.prototype, {
    _checkBeforeSendOrderReceipt(order) {
        return (
            super._checkBeforeSendOrderReceipt(...arguments) ||
            (order &&
                order.preset_id &&
                order.preset_id.identification !== "none" &&
                order.preset_id.sms_receipt_template_id)
        );
    },
});
