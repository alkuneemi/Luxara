import { test, expect } from "@odoo/hoot";
import { setupSelfPosEnv, getFilledSelfOrder } from "@pos_self_order/../tests/unit/utils";
import { definePosSelfModels } from "@pos_self_order/../tests/unit/data/generate_model_definitions";

definePosSelfModels();

test("_checkBeforeSendOrderReceipt", async () => {
    const store = await setupSelfPosEnv();
    const models = store.models;
    const order = await getFilledSelfOrder(store);
    const preset1 = models["pos.preset"].get(123); // Preset where identification is set to `Name` and `sms_receipt_template_id` is configured
    order.preset_id = preset1;
    expect(Boolean(store._checkBeforeSendOrderReceipt(order))).toBe(true);
    const preset2 = models["pos.preset"].get(10); // Preset where identification is set to `None` and `sms_receipt_template_id` is not configured
    order.preset_id = preset2;
    expect(Boolean(store._checkBeforeSendOrderReceipt(order))).toBe(false);
});
