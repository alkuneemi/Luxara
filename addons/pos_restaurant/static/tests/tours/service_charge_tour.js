import { registry } from "@web/core/registry";
import * as ChromePos from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

registry.category("web_tour.tours").add("ServiceChargeTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Test fixed amount service charge
            FloorScreen.clickTable("5"),
            Chrome.isTabActive("5"),
            ProductScreen.changeGuestNumber(1),
            ProductScreen.clickDisplayedProduct("Coca-Cola"),
            ProductScreen.orderlineIsToOrder("Coca-Cola"),
            Order.hasServiceCharge("10"), // Service charge should not change when adding a product with fixed amount.
            ProductScreen.totalAmountIs("12.20"),
            ProductScreen.changeGuestNumber(5),
            Order.hasServiceCharge("50"),
            ProductScreen.totalAmountIs("52.20"),

            // Test percentage service charge
            ProductScreen.selectPreset("Fixed", "Percentage before discount"),

            Order.hasServiceCharge("0.22"), // Service charge should be 10% of 2.20
            ProductScreen.totalAmountIs("2.42"),

            ProductScreen.clickDisplayedProduct("Bruschetta"),
            Order.hasServiceCharge("1.07"), // Service charge should be 10% of 10.70 (2.20 + 8.50)
            ProductScreen.totalAmountIs("11.77"),

            // Test percentage service charge based on order total before discount
            inLeftSide([...ProductScreen.addDiscount("10")]),
            Order.hasServiceCharge("1.07"), // Service charge should still be 10% of 10.70 because it's based on order total before discount
            ProductScreen.totalAmountIs("11.77"),

            // Test percentage service charge based on order total after discount
            ProductScreen.selectPreset("Percentage before discount", "Percentage after discount"),
            Order.hasServiceCharge("0.99"), // Service charge is (2.20 + 8.50 * 0.9) * 10% = 0.99
            ProductScreen.totalAmountIs("10.84"),

            // Test service charge receipt
        ].flat(),
});
