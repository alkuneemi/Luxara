import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import { delay } from "@web/core/utils/concurrency";
import * as PreparationReceipt from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import { checkPreparationTicketData } from "@point_of_sale/../tests/pos/tours/utils/preparation_receipt_util";
import { negateStep, assertCurrentOrderDirty } from "@point_of_sale/../tests/generic_helpers/utils";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("pos_restaurant_sync", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create a floating order. The idea is to have one of the draft orders be a floating order during the tour.
            FloorScreen.clickNewOrder(),

            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Test"),
            Chrome.clickPlanButton(),

            // Create first order
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            inLeftSide(Order.hasLine({ productName: "Coca-Cola", run: "dblclick" })),
            ProductScreen.clickDisplayedProduct("Water", true),
            ProductScreen.orderlineIsToOrder("Water"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            checkPreparationTicketData([
                { name: "Coca-Cola", qty: 1 },
                { name: "Water", qty: 1 },
            ]),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            ProductScreen.orderlinesHaveNoChange(),
            checkPreparationTicketData([]),
            ProductScreen.totalAmountIs("4.40"),

            // Create 2nd order (paid)
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            ProductScreen.totalAmountIs("4.40"),
            checkPreparationTicketData([
                { name: "Coca-Cola", qty: 1 },
                { name: "Minute Maid", qty: 1 },
            ]),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.closePrintingWarning(),
            FeedbackScreen.clickNextOrder(),

            // order on another table with a product variant
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", false),
            {
                ...Dialog.confirm(),
                content: "validate the variant dialog (with default values)",
            },
            ProductScreen.selectedOrderlineHas("Desk Organizer"),
            checkPreparationTicketData([
                { name: "Desk Organizer", qty: 1, attributes: ["S", "Leather"] },
            ]),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("4"),
            ProductScreen.orderlinesHaveNoChange(),
            checkPreparationTicketData([]),
            ProductScreen.orderLineHas("Desk Organizer", 1, 5.87),
            ProductScreen.totalAmountIs("5.87"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, {
                amount: 5.87,
            }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),

            // After clicking next order, floor screen is shown.
            // It should have 1 as number of draft synced order.
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            ProductScreen.totalAmountIs("4.40"),

            // Create another draft order and go back to floor
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("2"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true),
            ProductScreen.clickDisplayedProduct("Minute Maid", true),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("5", "0"),

            // Delete the first order then go back to floor
            Chrome.clickOrders(),
            // The order ref ends with -00002 because it is actually the 2nd order made in the session.
            // The first order made in the session is a floating order.
            TicketScreen.deleteOrder("002"),
            Dialog.confirm(),
            Chrome.closePrintingWarning(),
            Chrome.isSyncStatusConnected(),
            TicketScreen.selectOrder("005"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            Chrome.clickPlanButton(),

            // There should be 0 synced draft order as we already deleted -00002.
            FloorScreen.clickTable("5"),
            ProductScreen.orderIsEmpty(),
        ].flat(),
});

/* pos_restaurant_sync_second_login
 *
 * This tour should be run after the first tour is done.
 */
registry.category("web_tour.tours").add("pos_restaurant_sync_second_login", {
    steps: () =>
        [
            // There is one draft synced order from the previous tour
            Chrome.startPoS(),
            FloorScreen.clickTable("2"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(2)",
            },
            ProductScreen.totalAmountIs("4.40"),

            // Test transfering an order
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.orderCountSyncedInTableIs(2, 2),
            FloorScreen.clickTable("4"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(4)",
            },
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
                price: 2.2,
            }),
            Order.hasLine({
                productName: "Minute Maid",
                quantity: 1,
                withClass: ":eq(1)",
                price: 2.2,
            }),

            // Test if products still get merged after transfering the order
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickNumpad("1"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Chrome.closePrintingWarning(),
            FeedbackScreen.clickNextOrder(),
            // At this point, there are no draft orders.

            FloorScreen.clickTable("2"),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(2)",
            },
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.orderCountSyncedInTableIs(2, 0),
            FloorScreen.orderCountSyncedInTableIs(4, 0),
            FloorScreen.clickTable("4"),
            Chrome.waitRequest(),
            ProductScreen.isShown(),
            {
                trigger: ".pos-leftheader .badge:contains(4)",
            },
            ProductScreen.orderIsEmpty(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.orderCountSyncedInTableIs("4", "1"),
        ].flat(),
});

registry.category("web_tour.tours").add("SaveLastPreparationChangesTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "1"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(),
            ProductScreen.orderlinesHaveNoChange(),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_restaurant_course", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickCourseButton(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            // Check only 2 courses are there and empty course gets removed on clicking Order button
            negateStep(ProductScreen.checkCourseAtIndex(2, "Course 3")),
            ProductScreen.fireCourseButtonHighlighted("Course 2"),
            ProductScreen.payButtonNotHighlighted(),
            ProductScreen.clickCourseButton(),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            // Check only 2 courses are there and empty course gets removed on clicking Plan button
            negateStep(ProductScreen.checkCourseAtIndex(2, "Course 3")),
            // Check empty course gets remove after fire course.
            ProductScreen.clickCourseButton(),
            ProductScreen.selectCourseLine("Course 2"),
            {
                content: "Wait atleast 1 sec so that courses have different fired_date timestamps",
                trigger: "body",
                run: async () => await delay(1000),
            },
            ProductScreen.fireCourseButton(),
            Chrome.closePrintingWarning(),
            FloorScreen.clickTable("5"),
            negateStep(ProductScreen.checkCourseAtIndex(2, "Course 3")),
        ].flat(),
});

registry.category("web_tour.tours").add("OrderTrackingTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola", true, "2"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            inLeftSide([
                ...ProductScreen.clickLine("Coca-Cola", "2"),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "2"),
                ...["⌫", "1"].map(Numpad.click),
                ...ProductScreen.selectedOrderlineHasDirect("Coca-Cola", "1"),
            ]),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
registry.category("web_tour.tours").add("CrmTeamTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.emptyPaymentlines("2.20"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("4.40"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.clickPaymentlineDelButton("Bank", "2.20"),
            PaymentScreen.emptyPaymentlines("4.40"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSPaymentSyncTour3", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.clickTable("5"),
            PaymentScreen.isShown(),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("6.60"),
            ProductScreen.clickPayButton(false),
            PaymentScreen.remainingIs("2.2"),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.isShown(),
            ProductScreen.clickOrderButton(),
            Chrome.closePrintingWarning(),
            ProductScreen.orderlinesHaveNoChange(),
            Chrome.clickPlanButton(),
        ].flat(),
});

registry.category("web_tour.tours").add("LeaveResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),
            FloorScreen.hasTable("2"),
            FloorScreen.hasTable("4"),
            FloorScreen.hasTable("5"),
        ].flat(),
});

registry.category("web_tour.tours").add("FinishResidualOrder", {
    steps: () =>
        [
            Chrome.startPoS(),
            FloorScreen.orderCountSyncedInTableIs("5", "0"),
            FloorScreen.clickTable("5"),
            Order.hasLine({
                productName: "Coca-Cola",
                quantity: 1,
                withClass: ":eq(0)",
            }),
            ProductScreen.totalAmountIs("2.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.clickNextOrder(),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add(
        "test_fast_payment_validation_from_restaurant_product_screen_without_automatic_receipt_printing",
        {
            steps: () =>
                [
                    Chrome.startPoS(),
                    Dialog.confirm("Open Register"),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickFastPaymentButton("Bank"),
                    FeedbackScreen.isShown(),
                    Chrome.closePrintingWarning(),
                    FeedbackScreen.clickNextOrder(),
                    FloorScreen.isShown(),
                    FloorScreen.clickTable("2"),
                    ProductScreen.clickDisplayedProduct("Coca-Cola"),
                    {
                        content: "Check the content of the preparation receipt",
                        trigger: "body",
                        run: async () => {
                            const receipts = await PreparationReceipt.generatePreparationReceipts();
                            if (!receipts[0].innerHTML.includes("Coca-Cola")) {
                                throw new Error("Coca-Cola not found in printed receipt");
                            }
                            if (!receipts[0].innerHTML.includes("NEW")) {
                                throw new Error("NEW not found in printed receipt");
                            }
                        },
                    },
                    ProductScreen.clickPayButton(false),
                    PaymentScreen.clickPaymentMethod("Bank"),
                    PaymentScreen.clickValidate(),
                    FeedbackScreen.isShown(),
                    Chrome.closePrintingWarning(),
                    FeedbackScreen.clickNextOrder(),
                    FloorScreen.isShown(),
                ].flat(),
        }
    );

registry.category("web_tour.tours").add("test_transfering_orders", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Create a floating order with 3 cola
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.setTab("Cola"),
            Chrome.clickPlanButton(),

            // Create a floating order with 3 water
            FloorScreen.clickNewOrder(),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.clickDisplayedProduct("Water"),
            ProductScreen.setTab("Water"),
            Chrome.clickPlanButton(),

            // Create an order on table 5 with 3 minute maid
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            ProductScreen.clickDisplayedProduct("Minute Maid"),
            Chrome.clickPlanButton(),

            // Create an order on table 4 with 3 coca-cola
            FloorScreen.clickTable("4"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Chrome.clickPlanButton(),

            // Should have 4 orders
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_lines_qty_update", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Coca-Cola"),
            assertCurrentOrderDirty(false),
            Numpad.click("3"),
            Order.hasLine({ productName: "Coca-Cola", quantity: 3 }),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("5"),
            ProductScreen.isShown(),
            assertCurrentOrderDirty(false),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_partner", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            assertCurrentOrderDirty(false),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.addInternalNote("Hello world"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_line_note", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.addInternalNote("Demo note"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_sync_set_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            assertCurrentOrderDirty(false),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.clickPriceList("Second Pricelist"),
            assertCurrentOrderDirty(true),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_delete_line_release_table", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("5"),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            Order.hasLine({ productName: "Coca-Cola" }),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("5"),
            ProductScreen.clickLine("Coca-Cola"),
            ProductScreen.selectedOrderlineHasDirect("Coca-Cola"),
            ...["⌫", "⌫"].map(Numpad.click),
            ProductScreen.releaseTable(),
            FloorScreen.clickTable("5"),
            Chrome.waitRequest(),
            negateStep(...Order.hasLine({ productName: "Coca-Cola" })),
        ].flat(),
});

registry.category("web_tour.tours").add("test_futur_orders_are_not_cancelled", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Close Register"),
            Dialog.confirm("Close Register"),
            Dialog.confirm("Cancel Orders", ".btn-secondary"),
        ].flat(),
});
