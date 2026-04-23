import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/../tests/unit/data/product_template.data";

patch(ProductTemplate.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "tracking"];
    },
});

ProductTemplate._records = ProductTemplate._records.map((record) => ({
    ...record,
    tracking: record.tracking ?? "none",
}));
