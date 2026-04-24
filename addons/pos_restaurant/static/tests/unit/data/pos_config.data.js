import { PosConfig } from "@point_of_sale/../tests/unit/data/pos_config.data";

PosConfig._records = PosConfig._records.map((record) => ({
    ...record,
    module_pos_restaurant: true,
    floor_ids: [2, 3],
    iface_tipproduct: true,
    tip_product_id: 1,
    set_tip_after_payment: true,
    tip_percentage_1: 10,
    tip_percentage_2: 20,
    tip_percentage_3: 30,
    default_screen: "tables",
    floor_plan: {
        settings: {
            table_selection: "single",
            display_restaurant_name: true,
        },
        floors: [
            {
                id: 2,
                name: "Main Floor",
                floor_plan_layout: {
                    width: 1000,
                    height: 800,
                },
                tables: [
                    {
                        id: 1,
                        name: "Table 1",
                        table_number: 1,
                        floor_plan_layout: {
                            x: 100,
                            y: 150,
                            width: 100,
                            height: 100,
                        },
                    },
                    {
                        id: 2,
                        name: "Table 2",
                        table_number: 2,
                        floor_plan_layout: {
                            x: 300,
                            y: 150,
                            width: 100,
                            height: 100,
                        },
                    },
                ],
            },
            {
                id: 3,
                name: "Patio",
                floor_plan_layout: {
                    width: 1200,
                    height: 1000,
                },
                tables: [
                    {
                        id: 3,
                        name: "Table 1",
                        table_number: 1,
                        floor_plan_layout: {
                            x: 200,
                            y: 250,
                            width: 100,
                            height: 100,
                        },
                    },
                ],
            },
        ],
    },
}));
