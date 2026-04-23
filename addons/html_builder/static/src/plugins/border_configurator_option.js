import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";

const ROUND_CORNER_SIZES = [
    { value: 12, label: "Card" },
    { value: 100, label: "Pill" },
    { value: 8, label: "Large" },
    { value: 6, label: "Normal" },
    { value: 4, label: "Tiny" },
];

export class BorderConfigurator extends BaseOptionComponent {
    static template = "html_builder.BorderConfiguratorOption";
    static dependencies = ["builderActions"];
    static props = {
        label: { type: String },
        direction: { type: String, optional: true },
        withRoundCorner: { type: Boolean, optional: true },
        withBSClass: { type: Boolean, optional: true },
        action: { type: String, optional: true },
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        withRoundCorner: true,
        withBSClass: true, // TODO remove, and actually configure propertly in caller
        action: "styleAction",
    };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasBorder: this.hasBorder(editingElement),
        }));
        this.roundCornerSizes = ROUND_CORNER_SIZES;
    }
    getStyleActionParam(param) {
        const property = `border-${this.props.direction ? this.props.direction + "-" : ""}${param}`;
        if (this.props.withBSClass && (param === "width" || param === "radius")) {
            // grep: --box-border-width, --box-border-radius
            return `--box-${property}`;
        }
        return property;
    }
    hasBorder(editingElement) {
        const { getAction } = this.dependencies.builderActions;
        const styleActionValue = getAction("styleAction").getValue({
            editingElement,
            params: {
                mainParam: this.getStyleActionParam("width"),
            },
        });
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
}
