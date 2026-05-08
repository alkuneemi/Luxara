import { assignDefaultElementOptions, LayoutCell } from "../core/render_models";

export class MainTable extends LayoutCell {
    static template = "mail.MainTable";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.td = assignDefaultElementOptions(refs.td, {
            style: {
                padding: "0",
            },
        });
        super(options);
        this.setAttributes({
            style: {
                border: "0",
                "border-spacing": "0",
                width: "100%",
            },
            attributes: {
                align: "center",
                role: "presentation",
            },
        });
    }
}

export class MainTableLayout extends MainTable {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-layout",
        });
    }
}

export class MainTableWrapper extends MainTable {
    constructor(options = {}) {
        super(options);
        this.setAttributes({
            classNames: "o-ci-mail-wrapper",
        });
    }
}
