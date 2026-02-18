import {
    assignDefaultElementOptions,
    LayoutCell,
    LayoutModel,
    LayoutRow,
} from "../core/layout_models";

export class HybridFluidRow extends LayoutRow {
    static template = "mail.HybridFluidRow";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            // TODO EGGMAIL: RTL check
            style: {
                "text-align": "center",
            },
        });
        super(options);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-row",
            style: {
                "font-size": "0",
            },
        });
    }
}

export class HybridFluidCellWithOffset extends LayoutModel {
    static template = "mail.HybridFluidCellWithOffset";
    cell;
    offset;
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            style: {
                "max-width": "100%",
                "vertical-align": "top",
            },
        });
        super(options);
        this.cell = options.cell;
        this.offset = options.offset;
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-cell-with-offset",
            style: {
                display: "inline-block",
                width: "100%",
            },
        });
    }
}

export class HybridFluidCell extends LayoutCell {
    static template = "mail.HybridFluidCell";
    constructor(options = {}) {
        const refs = options.refs ?? {};
        options.refs = refs;
        refs.root = assignDefaultElementOptions(refs.root, {
            style: {
                "max-width": "100%",
                "vertical-align": "top",
            },
        });
        refs.styleContext = assignDefaultElementOptions(refs.styleContext, {
            // TODO EGGMAIL: RTL check
            style: {
                "text-align": "left",
                "font-size": "14px",
            },
        });
        super(options);
        this.setAttributes({
            classNames: "o-ci-hybrid-fluid-cell",
            style: {
                display: "inline-block",
                width: "100%",
            },
        });
    }
}

export class HybridFluidEmptyCell extends HybridFluidCell {
    constructor() {
        super(...arguments);
        this.setAttributes({
            style: {
                height: 0,
            },
        });
    }
}
