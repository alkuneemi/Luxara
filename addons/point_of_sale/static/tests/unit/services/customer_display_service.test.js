import { test, expect } from "@odoo/hoot";
import { getFilledOrder, setupPosEnv, expectFormattedPrice } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("_buildDisplayPayload", async () => {
    const store = await setupPosEnv();
    const customerDisplay = store.customerDisplay;
    const order = await getFilledOrder(store);

    const payload = customerDisplay._buildDisplayPayload(order);
    const lines = payload.lines;

    expect(lines).toHaveLength(2);
    expect(lines[0].isSelected).toBe(false);
    expect(lines[1].isSelected).toBe(true);
    expectFormattedPrice(payload.change, "$ 17.85");

    const prices = payload.extra_data.prices;
    expectFormattedPrice(prices.total_amount, "$ 17.85");
    expectFormattedPrice(prices.tax_amount, "$ 2.85");
    expectFormattedPrice(prices.subtotal_amount, "$ 15.00");
});
