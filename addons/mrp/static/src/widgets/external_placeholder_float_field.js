import { registry } from "@web/core/registry";
import { floatField, FloatField } from "@web/views/fields/float/float_field";
import { formatFloat } from "@web/views/fields/formatters";

const fieldRegistry = registry.category("fields");

class ExternalPlaceholderFloatField extends FloatField {
    static template = "mrp.ExternalPlaceholderFloatField";
    static props = {
        ...FloatField.props,
        placeholder: { type: String, optional: true },
    }

    get formattedValue() {
        return this.value ? super.formattedValue : "";
    }

    get placeholderValue() {
        const placeholder = this.props.record.data[this.props.placeholder];
        return placeholder !== undefined ? formatFloat(placeholder) : "...";
    }
}

fieldRegistry.add("external_placeholder_float_field", {
    ...floatField,
    component: ExternalPlaceholderFloatField,
    extractProps: ({ attrs, options }) => ({
        placeholder: attrs.placeholder,
    }),
});
