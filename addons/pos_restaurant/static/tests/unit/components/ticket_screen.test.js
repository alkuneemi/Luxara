import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

test("getTable and getTableTag include restaurant floor/table info", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = store.addNewOrder({ table_id: table });
    const screen = await mountWithCleanup(TicketScreen);

    expect(screen.getTableTag(order)).toBe(table.table_number);
    expect(screen.getTable(order)).toBe(`${table.floor_id.name}/${table.getName()}`);
});

test("_getSearchFields includes table number in restaurant mode", async () => {
    await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);

    const searchFields = screen._getSearchFields();
    expect(searchFields.REFERENCE.modelFields.includes("table_id.table_number")).toBe(true);
});

test("setOrder delegates to setTable for table orders", async () => {
    const store = await setupPosEnv();
    const table = store.models["restaurant.table"].get(2);
    const order = store.addNewOrder({ table_id: table });
    const screen = await mountWithCleanup(TicketScreen);
    let calledWith = null;

    store.setTable = async (calledTable, orderUuid) => {
        calledWith = { calledTable, orderUuid };
    };

    await screen.setOrder(order);

    expect(calledWith.calledTable).toBe(table);
    expect(calledWith.orderUuid).toBe(order.uuid);
});

test("isDefaultOrderEmpty always false in restaurant mode", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const screen = await mountWithCleanup(TicketScreen);

    expect(screen.isDefaultOrderEmpty(order)).toBe(false);
});

test("refund reuses current empty table order", async () => {
    const store = await setupPosEnv();
    const sourceTable = store.models["restaurant.table"].get(2);
    const currentTable = store.models["restaurant.table"].get(4);
    const partner = store.models["res.partner"].get(3);
    const cola = store.models["product.template"].get(5);
    const water = store.models["product.template"].get(6);

    const paidOrder = store.addNewOrder({ table_id: sourceTable });
    paidOrder.setPartner(partner);
    await store.addLineToOrder({ product_tmpl_id: cola, qty: 2 }, paidOrder);
    await store.addLineToOrder({ product_tmpl_id: water, qty: 1 }, paidOrder);
    paidOrder.state = "paid";

    const currentTableOrder = store.addNewOrder({ table_id: currentTable });
    currentTableOrder.setPartner(partner);
    store.setOrder(currentTableOrder);

    const screen = await mountWithCleanup(TicketScreen);
    screen.setSelectedOrder(paidOrder);
    const colaLine = paidOrder.lines.find((line) => line.product_id.product_tmpl_id.id === cola.id);
    screen.getToRefundDetail(colaLine).qty = 2;

    await screen.onDoRefund();

    const refundOrder = store.getOrder();
    const refundedCola = refundOrder.lines.find(
        (line) => line.refunded_orderline_id?.id === colaLine.id
    );

    expect(refundOrder.uuid).toBe(currentTableOrder.uuid);
    expect(refundOrder.table_id.id).toBe(currentTable.id);
    expect(refundOrder.is_refund).toBe(true);
    expect(refundedCola.qty).toBe(-2);
    expect(refundOrder.getScreenData().name).toBe("PaymentScreen");
});
