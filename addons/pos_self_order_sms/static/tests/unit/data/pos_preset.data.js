import { patch } from "@web/core/utils/patch";
import { PosPreset } from "@point_of_sale/../tests/unit/data/pos_preset.data";

patch(PosPreset.prototype, {
    _load_pos_data_fields() {
        return [...super._load_pos_data_fields(), "sms_receipt_template_id"];
    },
});

PosPreset._records = [
    ...PosPreset._records,
    {
        id: 123,
        name: "Takeout with SMS Receipt",
        identification: "name",
        available_in_self: true,
        sms_receipt_template_id: 1,
    },
];
