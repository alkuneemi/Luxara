import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";

export class BgBlurOption extends BaseOptionComponent {
    static template = "website.BgBlurOption";

    static props = {
        level: { type: Number, optional: true },
    };
    static defaultProps = {
        level: 2,
    };

    setup() {
        super.setup();
        this.blurState = useDomState((el) => {
            const target = this.props.applyTo ? el.querySelector(this.props.applyTo) : el;
            // Matches website bg overlay utilities: bg-black-15, bg-white-50, etc.
            const websiteBgOverlayClasses = new Set([
                'bg-black-15', 'bg-black-25', 'bg-black-50', 'bg-black-75',
                'bg-white-15', 'bg-white-25', 'bg-white-50', 'bg-white-75',
            ]);
            return {
                show:
                    target?.style.backgroundColor.startsWith("rgba") ||
                    target?.style.backgroundImage.includes("rgba") ||
                    [...(target?.classList ?? [])].some(className => websiteBgOverlayClasses.has(className)) ||
                    false,
                hasBlur: target?.style.getPropertyValue("--o-bg-blur") > 0,
            };
        });
    }
}
