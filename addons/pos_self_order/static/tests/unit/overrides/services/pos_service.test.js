import { test, expect, describe } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { setupPoSEnvForSelfOrder } from "../../utils";
import { DeliveryButton } from "@point_of_sale/app/components/delivery_button/delivery_button";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

definePosModels();

describe("pos_store.js", () => {
    test("check self_ordering_table_id", async () => {
        const store = await setupPoSEnvForSelfOrder();
        const deliveryButtons = await mountWithCleanup(DeliveryButton);
        const table = store.models["restaurant.table"].getFirst();

        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);

        const order1 = await getFilledOrder(store, { table_id: table });

        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        order1.state = "cancel";
        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);

        const order2 = await getFilledOrder(store, { self_ordering_table_id: table });
        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        // Avoid doublon
        order2.table_id = table;
        expect(store.tableHasOrders(table)).toBe(true);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(1);
        expect(store.getTableOrders(table.id)).toHaveLength(1);

        order2.state = "cancel";
        expect(store.tableHasOrders(table)).toBe(false);
        expect(store.getActiveOrdersOnTable(table)).toHaveLength(0);
        expect(store.getTableOrders(table)).toHaveLength(0);

        // check ongoing order count
        const order3 = await getFilledOrder(store, { table_id: table });
        order3.source = "mobile";
        const order4 = await getFilledOrder(store, { table_id: table });
        expect(deliveryButtons.ongoingOrders).toBe(1);
        order4.source = "mobile";
        expect(deliveryButtons.ongoingOrders).toBe(2);
        order3.state = "paid";
        expect(deliveryButtons.ongoingOrders).toBe(1);
    });
});
