import { CarouselSlider } from "@website/interactions/carousel/carousel_slider";
import { registry } from "@web/core/registry";

const CarouselSliderEdit = (I) =>
    class extends I {
        dynamicContent = {
            ...this.dynamicContent,
            _root: {
                ...this.dynamicContent._root,
                "t-on-content_changed": this.onContentChanged,
            },
            ".carousel-control-prev, .carousel-control-next": {
                "t-on-click": () => this.computeMaxHeight(),
            },
        };
        // Pause carousel in edit mode.
        carouselOptions = { ride: false, pause: true, keyboard: false };
        showClickableSlideLinks = false;

        start() {
            super.start();
            // Recompute the carousel height when its classes change.
            // This covers scenarios where a custom snippet applies
            // `o_full_screen_height` and later resets it to `auto`
            // (e.g., after sliding the carousel), ensuring the correct
            // min-height is reapplied to carousel items.
            const sectionEl = this.el.closest("section");
            if (sectionEl) {
                this.carouselClassObserver = new MutationObserver((mutationRecords) => {
                    for (const mutation of mutationRecords) {
                        const prevValue = mutation.oldValue || "";
                        const HEIGHT_CLASSES = ["o_full_screen_height", "o_three_quarter_height"];
                        const previousHeightClass = HEIGHT_CLASSES.find((cls) =>
                            prevValue.includes(cls)
                        );
                        const currentHeightClass = HEIGHT_CLASSES.find((cls) =>
                            sectionEl.classList.contains(cls)
                        );

                        if (previousHeightClass !== currentHeightClass) {
                            this.computeMaxHeight();
                            break;
                        }
                    }
                });
                this.carouselClassObserver.observe(sectionEl, {
                    attributes: true,
                    attributeFilter: ["class"],
                    attributeOldValue: true,
                });
                this.registerCleanup(() => this.carouselClassObserver.disconnect());
            }
        }
        onContentChanged() {
            this.computeMaxHeight();
        }
    };

registry.category("public.interactions.edit").add("website.carousel_slider", {
    Interaction: CarouselSlider,
    mixin: CarouselSliderEdit,
});
