import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { describe, expect, test } from "@odoo/hoot";
import { click, queryOne } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { switchToEditMode } from "../../helpers";
import { startInteractionsWithSnippet } from "../helpers";
import { registry } from "@web/core/registry";

setupInteractionWhiteList("website.carousel_bootstrap_upgrade_fix");

describe.current.tags("interaction_dev");

test("[EDIT] carousel_bootstrap_upgrade_fix prevents ride", async () => {
    const { core } = await startInteractionsWithSnippet("s_image_gallery");
    expect(core.interactions).toHaveLength(1);
    await switchToEditMode(core);
    const carouselEl = queryOne(".carousel");
    const carouselBS = window.Carousel.getInstance(carouselEl);
    expect(carouselBS._config.ride).toBe(false);
    expect(carouselBS._config.pause).toBe(true);
});

test("carousel_bootstrap_upgrade_fix is tagged while sliding", async () => {
    registry
        .category("html_builder.snippetsPreprocessor")
        .add("test_snippets", function (namespace, snippets) {
            const carouselEl = snippets.querySelector("[data-snippet='s_image_gallery'] .carousel");
            Object.assign(carouselEl.dataset, {
                bsInterval: 5000,
            });
        });
    const { core } = await startInteractionsWithSnippet("s_image_gallery");
    expect(core.interactions).toHaveLength(1);

    const carouselEl = queryOne(".carousel");
    expect(carouselEl).toHaveAttribute("data-bs-interval", "5000");
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");

    await click(carouselEl.querySelector(".carousel-control-next"));

    expect(carouselEl).toHaveClass("o_carousel_sliding");
    await advanceTime(750);
    expect(carouselEl).not.toHaveClass("o_carousel_sliding");
});
