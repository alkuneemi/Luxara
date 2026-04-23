import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useClickableBuilderComponent, clickableBuilderComponentProps } from "../utils";
import { BuilderComponent } from "./builder_component";

export class BuilderDropdownItem extends Component {
    static template = "html_builder.BuilderDropdownItem";

    static props = {
        ...clickableBuilderComponentProps,
        class: { type: [String, Object], optional: true },
        // Why do you need the attrs prop?
        attrs: { type: Object, optional: true },
        slots: { type: Object, optional: true },
    };

    static defaultProps = {
        class: "",
        attrs: {},
    };

    static components = { BuilderComponent, DropdownItem };

    setup() {
        const { operation } = useClickableBuilderComponent();
        this.operation = operation;
    }

    get pointerAttrs() {
        return {
            ...this.props.attrs,
        };
    }

    onSelected() {
        this.operation.commit();
    }
}
