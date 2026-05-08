import { test, expect } from "@odoo/hoot";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

definePosModels();

test("addProductToOrder", async () => {
    const store = await setupPosEnv();
    const models = store.models;
    const order = store.addNewOrder();

    order.config.use_course_allocation = true;

    const product1 = models["product.template"].get(5);
    const product2 = models["product.template"].get(6);
    const product3 = models["product.template"].get(12);

    const screen = await mountWithCleanup(ProductScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });

    await screen.addProductToOrder(product1);

    expect(order.getOrderlines()).toHaveLength(1);
    expect(order.courses).toHaveLength(1);
    expect(order.courses[0].name).toBe("Default Course 1");

    await screen.addProductToOrder(product2);

    expect(order.getOrderlines()).toHaveLength(2);
    expect(order.courses).toHaveLength(2);
    expect(order.courses[1].name).toBe("Default Course 2");

    await screen.addProductToOrder(product3);

    expect(order.getOrderlines()).toHaveLength(3);
    expect(order.courses).toHaveLength(2);
});

test("breakCombo with course allocation", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    order.config.use_course_allocation = true;

    const product1 = store.models["product.template"].get(7);
    const product2 = store.models["product.product"].get(8);

    product2.pos_categ_ids = [1];

    const screen = await mountWithCleanup(ProductScreen, {
        props: {
            orderUuid: order.uuid,
        },
    });
    screen.addProductToOrder(product1);

    await contains(".modal-dialog article[data-product-id='8']").click();
    await contains(".modal-dialog article[data-product-id='10']").click();
    await contains("button:contains('Add to order')").click();

    expect(order.courses[0].name).toBe("Default Course 2");
    expect(order.courses).toHaveLength(1);

    store.breakCombo(order.lines[0]);

    expect(order.courses[0].name).toBe("Default Course 1");
    expect(order.courses[1].name).toBe("Default Course 2");
    expect(order.courses).toHaveLength(2);

    order.removeOrderline(order.lines[0]);

    expect(order.getOrderlines()).toHaveLength(1);
    expect(order.courses).toHaveLength(1);
    expect(order.courses[0].name).toBe("Default Course 2");
});
