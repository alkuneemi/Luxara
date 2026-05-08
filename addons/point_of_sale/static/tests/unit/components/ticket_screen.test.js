import { test, expect, describe } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { setupPosEnv, makeOrder } from "@point_of_sale/../tests/unit/utils";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
const { DateTime } = luxon;

definePosModels();

test("_onUpdateSelectedOrderline: refund moves to next", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();

    const comboLine = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(7),
        payload: [
            [
                { combo_item_id: store.models["product.combo.item"].get(1), qty: 1 },
                { combo_item_id: store.models["product.combo.item"].get(3), qty: 1 },
            ],
            [],
        ],
        configure: false,
    });
    const line2Refund = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(8),
        qty: 2,
    });

    const line1 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(5),
        qty: 3,
    });
    const line2 = await store.addLineToCurrentOrder({
        product_tmpl_id: store.models["product.template"].get(6),
    });
    order.state = "paid";

    // refund `line2Refund`
    const refundedOrder = store.createNewOrder();
    const refundingLine = await store.addLineToOrder(
        { product_tmpl_id: store.models["product.template"].get(8), qty: -2 },
        refundedOrder
    );
    line2Refund.refund_orderline_ids = [refundingLine.id];
    refundedOrder.state = "paid";

    const ticketScreen = await mountWithCleanup(TicketScreen);
    ticketScreen.onClickOrder(order);
    expect(ticketScreen.getSelectedOrderlineId()).toBe(comboLine.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "1" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "2" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line1.id);
    ticketScreen._onUpdateSelectedOrderline({ key: "Enter", buffer: "3" });
    expect(ticketScreen.getSelectedOrderlineId()).toBe(line2.id);
});

test("activeOrderFilter", async () => {
    const store = await setupPosEnv();
    const order = store.addNewOrder();
    const screen = await mountWithCleanup(TicketScreen);

    order.getScreenData = () => ({ name: "PaymentScreen" });
    order.state = "draft";
    expect(screen.activeOrderFilter(order)).toBe(true);
    order.state = "cancel";
    expect(screen.activeOrderFilter(order)).toBe(true);
    order.state = "paid";
    expect(screen.activeOrderFilter(order)).toBe(false);
    order.getScreenData = () => ({ name: "TipScreen" });
    expect(screen.activeOrderFilter(order)).toBe(true);
});

describe("getFilteredOrderList", () => {
    // --- Filter: SYNCED vs ACTIVE ---
    test("SYNCED returns only finalized orders", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", state: "draft" }); // not finalized
        makeOrder(store, { pos_reference: "O-02", state: "cancel" }); // finalized but cancelled
        makeOrder(store, { pos_reference: "O-03", state: "paid" }); // finalized and paid

        screen.state.filter = "SYNCED";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-03");
    });

    test("ACTIVE_ORDERS uses activeOrderFilter", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", state: "draft" });
        makeOrder(store, {
            pos_reference: "O-02",
            state: "paid",
            getScreenData: () => ({ name: "PaymentScreen" }),
        });

        screen.state.filter = "ACTIVE_ORDERS";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    // --- Secondary filter: CANCELLED ---
    test("CANCELLED filters to cancel state only", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", state: "draft" });
        makeOrder(store, { pos_reference: "O-02", state: "cancel" });

        screen.state.filter = "CANCELLED";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-02");
    });

    // --- Secondary filter: screen-based (e.g. PAYMENT) ---
    test("screen-based filter maps correctly", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, {
            pos_reference: "O-01",
            state: "draft",
            getScreenData: () => ({ name: "PaymentScreen" }),
        });
        makeOrder(store, {
            pos_reference: "O-02",
            state: "draft",
            getScreenData: () => ({ name: "ProductScreen" }),
        });

        screen.state.filter = "PAYMENT";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    // --- Search ---
    test("searchTerm applies fuzzyLookup", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01" });
        makeOrder(store, { pos_reference: "O-02" });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.search = { fieldName: "RECEIPT_NUMBER", searchTerm: "O-01" };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    test("partnerId filters to that partner when fieldName is PARTNER", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", partner_id: { id: 1 } });
        makeOrder(store, { pos_reference: "O-02", partner_id: { id: 2 } });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.search = { fieldName: "PARTNER", searchTerm: "", partnerId: 1 };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    // --- Preset ---
    test("selectedPreset filters by preset_id", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", preset_id: { id: 10, use_timing: false } });
        makeOrder(store, { pos_reference: "O-02", preset_id: { id: 20, use_timing: false } });

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.selectedPreset = { id: 10, use_timing: false };
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(1);
        expect(result[0].pos_reference).toBe("O-01");
    });

    // --- Sorting ---
    test("ACTIVE sorts ascending by date", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, { pos_reference: "O-01", date_order: DateTime.now().minus({ hours: 1 }) });
        makeOrder(store, { pos_reference: "O-02", date_order: DateTime.now() });

        screen.state.filter = "ACTIVE_ORDERS";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(2);
        expect(result[0].pos_reference).toBe("O-01");
        expect(result[1].pos_reference).toBe("O-02");
    });

    test("SYNCED sorts descending by date", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        makeOrder(store, {
            pos_reference: "O-01",
            state: "paid",
            date_order: DateTime.now().minus({ hours: 1 }),
        });
        makeOrder(store, {
            pos_reference: "O-02",
            state: "paid",
            date_order: DateTime.now(),
        });

        screen.state.filter = "SYNCED";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(2);
        expect(result[0].pos_reference).toBe("O-02");
        expect(result[1].pos_reference).toBe("O-01");
    });

    test("same date falls back to pos_reference number sort", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        const now = DateTime.now();
        makeOrder(store, { date_order: now, pos_reference: "O-02" });
        makeOrder(store, { date_order: now, pos_reference: "O-01" });

        screen.state.filter = "ACTIVE_ORDERS";
        const result = screen.getFilteredOrderList();

        expect(result.length).toBe(2);
        expect(result[0].pos_reference).toBe("O-01");
        expect(result[1].pos_reference).toBe("O-02");
    });

    // --- use_timing preset sort ---
    test("use_timing sorts unfinished timers first, ascending", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);
        const preset = store.models["pos.preset"].get(2);

        const urgent = makeOrder(store, {
            pos_reference: "O-01",
            preset_id: preset,
        });
        const done = makeOrder(store, {
            pos_reference: "O-02",
            preset_id: preset,
        });

        screen.state.selectedPreset = preset;
        screen.state.filter = "ACTIVE_ORDERS";
        screen.orderTimers = {
            [urgent.uuid]: 30, // 30s left — not finished
            [done.uuid]: 0, // finished
        };

        const result = screen.getFilteredOrderList();
        expect(result.length).toBe(2);
        expect(result[0].pos_reference).toBe("O-01");
        expect(result[1].pos_reference).toBe("O-02");
    });

    // --- Pagination ---
    test("pagination slices correctly", async () => {
        const store = await setupPosEnv();
        const screen = await mountWithCleanup(TicketScreen);

        for (let i = 0; i < 5; i++) {
            makeOrder(store, { pos_reference: `O-0${i + 1}` });
        }

        screen.state.filter = "ACTIVE_ORDERS";
        screen.state.nbrByPage = 2;
        screen.state.page = 2;

        const result = screen.getFilteredOrderList();
        expect(result.length).toBe(2);
    });
});

test("getStatus", async () => {
    const store = await setupPosEnv();
    const screen = await mountWithCleanup(TicketScreen);
    const order = makeOrder(store, { state: "cancel" });

    expect(screen.getStatus(order)).toBe("Cancelled");

    order.state = "paid";
    order.getScreenData = () => ({ name: "" });
    expect(screen.getStatus(order)).toBe("Paid");

    order.getScreenData = () => ({ name: "PaymentScreen" });
    screen.state.filter = "SYNCED";
    expect(screen.getStatus(order)).toBe("Paid");

    order.state = "draft";
    screen.state.filter = "ACTIVE_ORDERS";
    expect(screen.getStatus(order)).toBe("Payment");
});
