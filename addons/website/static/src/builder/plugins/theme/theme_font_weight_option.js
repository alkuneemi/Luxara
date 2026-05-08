import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { _t } from "@web/core/l10n/translation";
import { CustomizeWebsiteVariableAction } from "../customize_website_plugin";

const FONT_WEIGHT_OPTIONS = [
    { label: _t("Thin"), value: 100 },
    { label: _t("Extra Light"), value: 200 },
    { label: _t("Light"), value: 300 },
    { label: _t("Regular"), value: 400 },
    { label: _t("Medium"), value: 500 },
    { label: _t("Semi Bold"), value: 600 },
    { label: _t("Bold"), value: 700 },
    { label: _t("Extra Bold"), value: 800 },
    { label: _t("Black"), value: 900 },
];

function unquote(value) {
    if (value.startsWith("'")) {
        return value.substring(1, value.length - 1);
    }
    return value;
}

function getParsedWeight(value) {
    if (value === "") {
        return null;
    }
    return parseInt(`${value}`.trim());
}

function parseFontFaceWeight(weightDescriptor) {
    const tokens = `${weightDescriptor || ""}`.trim().split(/\s+/).filter(Boolean);
    if (!tokens.length) {
        return [];
    }
    if (tokens.length === 2) {
        const min = getParsedWeight(tokens[0]);
        const max = getParsedWeight(tokens[1]);
        if (min !== null && max !== null) {
            return FONT_WEIGHT_OPTIONS.filter(
                ({ value }) => value >= Math.min(min, max) && value <= Math.max(min, max)
            ).map(({ value }) => value);
        }
    }
    const weight = getParsedWeight(tokens[0]);
    return weight === null ? [] : [weight];
}

export class FontWeightPicker extends BaseOptionComponent {
    static template = "website.FontWeightPicker";
    static props = {
        variable: { type: String },
        weights: { type: Array },
        disabled: { type: Boolean, optional: true },
    };
    static defaultProps = {
        disabled: false,
    };
}

export class ThemeFontWeightOption extends BaseOptionComponent {
    static template = "website.ThemeFontWeightOption";
    static components = { FontWeightPicker };
    static dependencies = ["themeTab"];
    static props = {
        fontVariable: { type: String },
        regularVariable: { type: String, optional: true },
        lightVariable: { type: String, optional: true },
        boldVariable: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.state = useDomState(async () => {
            const fontName = this.getFontName(getHtmlStyle(this.document));
            const availableWeights = await this.getAvailableWeights(fontName);
            const regularWeight = this.getCurrentWeight(this.props.regularVariable);
            return {
                availableWeights,
                regularWeight,
            };
        });
    }

    get boldTooltip() {
        return this.isBoldDisabled ? _t("This font is missing font weight") : undefined;
    }

    get filteredLightWeights() {
        return this.getFilteredWeights("light");
    }

    get filteredBoldWeights() {
        return this.getFilteredWeights("bold");
    }

    get isBoldDisabled() {
        return !this.filteredBoldWeights.length;
    }

    getFilteredWeights(type) {
        const { availableWeights, regularWeight } = this.state;
        if (regularWeight === null) {
            return availableWeights;
        }
        return availableWeights.filter(({ value }) =>
            type === "light" ? value <= regularWeight : value >= regularWeight
        );
    }

    getFontName(style) {
        return unquote(getCSSVariableValue(this.props.fontVariable, style));
    }

    async getAvailableWeights(rawFontName) {
        const fontName = unquote(rawFontName);
        const cachedWeights = this.dependencies.themeTab.getCachedFontWeights(fontName);
        if (cachedWeights) {
            return cachedWeights;
        }
        const availableWeightValues = new Set();
        if (fontName && this.document.fonts) {
            await this.document.fonts.ready;
            for (const fontFace of this.document.fonts) {
                if (unquote(fontFace.family) !== fontName) {
                    continue;
                }
                for (const weight of parseFontFaceWeight(fontFace.weight)) {
                    availableWeightValues.add(weight);
                }
            }
        }
        const availableWeights = FONT_WEIGHT_OPTIONS.filter(({ value }) =>
            availableWeightValues.has(value)
        );
        this.dependencies.themeTab.setCachedFontWeights(fontName, availableWeights);
        return availableWeights;
    }

    getCurrentWeight(weightVariable) {
        if (!weightVariable) {
            return null;
        }
        return (
            getParsedWeight(getCSSVariableValue(weightVariable, getHtmlStyle(this.document))) ||
            null
        );
    }
}

export class CustomizeWebsiteFontWeightAction extends CustomizeWebsiteVariableAction {
    static id = "customizeWebsiteFontWeight";

    normalizeValue(value) {
        if (value === null) {
            return null;
        }
        const parsedValue = getParsedWeight(value);
        return parsedValue === null ? null : `${parsedValue}`;
    }

    getValue({ params }) {
        const rawValue = getCSSVariableValue(params.mainParam, getHtmlStyle(this.document));
        return this.normalizeValue(rawValue);
    }

    isApplied({ params, value }) {
        return this.getValue({ params }) === this.normalizeValue(value);
    }
}
