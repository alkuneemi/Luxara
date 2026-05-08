import { normalizeCSSColor } from "@web/core/utils/colors";

export const PALETTE_NAMES = [
    "default-light-1",
    "default-light-2",
    "default-light-4",
    "default-light-3",
    "default-light-5",
    "default-24",
    "default-light-7",
    "default-light-6",
    "default-light-11",
    "default-light-14",
    "default-light-8",
    "default-6",
    "default-7",
    "default-8",
    "default-9",
    "default-23",
    "default-25",
    "default-12",
    "default-14",
    "default-22",
    "default-15",
    "default-16",
    "default-17",
    "default-light-10",
    "default-19",
    "default-20",
    "default-5",
    "default-4",
    "default-light-9",
    "default-2",
    "default-light-13",
    "default-27",
    "default-light-12",
    "default-1",
    "default-28",
    "default-21",
];

export const CUSTOM_BG_COLOR_ATTRS = ["menu", "footer"];

function getCSSVariableValue(key, style) {
    return normalizeCSSColor(style.getPropertyValue(`--${key}`).trim()).replace(/"/g, "'");
}

// Columns = font class (Sans Serif, Serif, Script, Decorative, Gothic),
// rows = color palettes.
export const PALETTE_FONT_COMBOS = [
    // Row 1
    {
        palette: "default-light-2",
        headingsFont: "Roboto",
        bodyFont: "Inter",
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-light-2",
        headingsFont: "Playfair Display",
        bodyFont: "Source Sans Pro",
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-light-2",
        headingsFont: "Dancing Script",
        bodyFont: "Open Sans",
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-light-2",
        headingsFont: "Lobster",
        bodyFont: "Roboto",
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-light-2",
        headingsFont: "Oswald",
        bodyFont: "Inter",
        label: "Bold",
        description: "Strong & Striking",
    },
    // Row 2
    {
        palette: "default-light-5",
        headingsFont: "Inter Tight",
        bodyFont: "Source Sans Pro",
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-light-5",
        headingsFont: "Noto Serif",
        bodyFont: "Inter",
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-light-5",
        headingsFont: "Caveat",
        bodyFont: "Source Sans Pro",
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-light-5",
        headingsFont: "Fredoka One",
        bodyFont: "Open Sans",
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-light-5",
        headingsFont: "Anton",
        bodyFont: "Roboto",
        label: "Bold",
        description: "Strong & Striking",
    },
    // Row 3
    {
        palette: "default-light-7",
        headingsFont: "Raleway",
        bodyFont: "Open Sans",
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-light-7",
        headingsFont: "Arvo",
        bodyFont: "Open Sans",
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-light-7",
        headingsFont: "Pacifico",
        bodyFont: "Inter",
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-light-7",
        headingsFont: "Baloo 2",
        bodyFont: "Inter",
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-light-7",
        headingsFont: "Bebas Neue",
        bodyFont: "Source Sans Pro",
        label: "Bold",
        description: "Strong & Striking",
    },
    // Row 4
    {
        palette: "default-24",
        headingsFont: "Roboto",
        bodyFont: "Inter",
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-24",
        headingsFont: "Playfair Display",
        bodyFont: "Source Sans Pro",
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-24",
        headingsFont: "Dancing Script",
        bodyFont: "Open Sans",
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-24",
        headingsFont: "Lobster",
        bodyFont: "Roboto",
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-24",
        headingsFont: "Oswald",
        bodyFont: "Inter",
        label: "Bold",
        description: "Strong & Striking",
    },
    // Row 5
    {
        palette: "default-light-11",
        headingsFont: "Inter Tight",
        bodyFont: "Source Sans Pro",
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-light-11",
        headingsFont: "Noto Serif",
        bodyFont: "Inter",
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-light-11",
        headingsFont: "Caveat",
        bodyFont: "Source Sans Pro",
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-light-11",
        headingsFont: "Fredoka One",
        bodyFont: "Open Sans",
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-light-11",
        headingsFont: "Anton",
        bodyFont: "Inter",
        label: "Bold",
        description: "Strong & Striking",
    },
    // Row 6 (dark)
    {
        palette: "default-9",
        headingsFont: "Raleway",
        bodyFont: "Open Sans",
        dark: true,
        label: "Modern",
        description: "Clean & Efficient",
    },
    {
        palette: "default-9",
        headingsFont: "Arvo",
        bodyFont: "Open Sans",
        dark: true,
        label: "Classic",
        description: "Timeless & Refined",
    },
    {
        palette: "default-9",
        headingsFont: "Pacifico",
        bodyFont: "Inter",
        dark: true,
        label: "Creative",
        description: "Warm & Personal",
    },
    {
        palette: "default-9",
        headingsFont: "Baloo 2",
        bodyFont: "Inter",
        dark: true,
        label: "Playful",
        description: "Fun & Friendly",
    },
    {
        palette: "default-9",
        headingsFont: "Bebas Neue",
        bodyFont: "Source Sans Pro",
        dark: true,
        label: "Bold",
        description: "Strong & Striking",
    },
];

export function getCSSPaletteNames(style) {
    return getCSSVariableValue("palette-names", style)
        .split(", ")
        .map((name) => name.replace(/'/g, ""));
}

export function getCSSPalettes(style, paletteNames = getCSSPaletteNames(style), bgColorAttrs = []) {
    const palettes = {};
    for (const paletteName of paletteNames) {
        const palette = {
            name: paletteName,
        };
        for (let j = 1; j <= 5; j += 1) {
            palette[`color${j}`] = getCSSVariableValue(
                `o-palette-${paletteName}-o-color-${j}`,
                style
            );
        }
        for (const attr of bgColorAttrs) {
            palette[attr] = getCSSVariableValue(`o-palette-${paletteName}-${attr}-bg`, style);
        }
        palettes[paletteName] = palette;
    }
    return palettes;
}

export function getPaletteFontCombos(palettes) {
    return PALETTE_FONT_COMBOS.map((combo) => {
        const colors = palettes[combo.palette];
        if (!colors) {
            return null;
        }
        return {
            ...combo,
            colors,
            bgColor: combo.dark ? colors.color5 : colors.color3,
            textColor: combo.dark ? colors.color4 : colors.color5,
        };
    }).filter(Boolean);
}
