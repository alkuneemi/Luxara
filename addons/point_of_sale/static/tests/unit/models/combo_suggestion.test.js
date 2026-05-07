import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { ComboSuggestion } from "@point_of_sale/app/models/utils/combo_suggestion";

definePosModels();

function getComboSuggestion(store) {
    return new ComboSuggestion(store.models, store.currency, store.company, store.config);
}

test("groups upsell suggestions and keeps only free combo values", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    await store.addLineToOrder({ product_tmpl_id: 8 }, order);
    await store.addLineToOrder({ product_tmpl_id: 10 }, order);

    const comboSuggestion = getComboSuggestion(store);
    const potentialCombos = comboSuggestion.getPotentialCombos(order);

    expect(potentialCombos.applicable).toHaveLength(0);
    expect(potentialCombos.upsell).toHaveLength(1);
    expect(potentialCombos.upsell[0].product.id).toBe(7);
    expect(
        comboSuggestion
            .getComboValuesFromCombination(potentialCombos.upsell[0].combinations[0])
            .map((item) => item.combo_item_id.id)
    ).toEqual([1, 3]);
});

test("builds combo payloads for direct non-upsell combos", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const comboProduct = store.models["product.product"].get(7);
    const combo1 = store.models["product.combo"].get(1);
    combo1.is_upsell = false;
    combo1.qty_free = combo1.qty_max = 1;

    await store.addLineToOrder({ product_tmpl_id: 8 }, order);
    await store.addLineToOrder({ product_tmpl_id: 10 }, order);

    const comboSuggestion = getComboSuggestion(store);
    const matchingCombo = comboSuggestion.getApplicableProductCombo(order, "combinations")[0];

    expect(matchingCombo.product.id).toBe(comboProduct.id);
    expect(matchingCombo.combinationsQty).toBe(1);
    expect(
        comboSuggestion
            .getComboValuesFromCombination(matchingCombo.combinations[0])
            .map((item) => item.combo_item_id.id)
    ).toEqual([1, 3]);
});
