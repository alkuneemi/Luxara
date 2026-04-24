import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";

definePosModels();

test("tip updates selected payment line amount by remaining balance", async () => {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const bank = store.models["pos.payment.method"].get(2);
    const screen = await mountWithCleanup(PaymentScreen, {
        props: { orderUuid: order.uuid },
    });

    await screen.addNewPaymentLine(bank);
    const line = order.getSelectedPaymentline();

    store.setTip = async () => {};

    // case 1: remaining <= 0 -> increase payment line by full tip difference
    line.setAmount(1);
    await screen.onNewTip({
        newValue: 1,
        type: "fixed",
        currentTipAmount: 0,
        change: 0,
    });
    expect(line.getAmount()).toBe(2);

    // case 2: remaining > 0 and remaining >= tip -> do not change payment line amount
    line.setAmount(5);
    await screen.onNewTip({
        newValue: 2,
        type: "fixed",
        currentTipAmount: 0,
        change: 2,
    });
    expect(line.getAmount()).toBe(5);

    // case 3: remaining > 0 and remaining < tip -> increase by the difference
    line.setAmount(5);
    await screen.onNewTip({
        newValue: 3,
        type: "fixed",
        currentTipAmount: 0,
        change: 2,
    });
    expect(line.getAmount()).toBe(6);
});
