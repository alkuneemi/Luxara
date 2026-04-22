// import { delay } from "@web/core/utils/concurrency";
import {
    clickOnSnippet,
    insertSnippet,
    registerWebsitePreviewTour,
    changeBackgroundShape,
} from "@website/js/tours/tour_utils";

function removeSelectedBlock() {
    return {
        content: "Remove selected block",
        trigger: ".overlay .oe_snippet_remove",
        run: "click",
    };
}

registerWebsitePreviewTour(
    "snippet_empty_parent_autoremove",
    {
        edition: true,
    },
    () => [
        // Base case: remove both columns from text - image
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Click on second column",
            trigger: ":iframe #wrap .s_text_image .row > :nth-child(2)",
            run: "click",
        },
        removeSelectedBlock(),
        {
            content: "Click on first column",
            trigger: ":iframe #wrap .s_text_image .row > :first-child",
            run: "click",
        },
        removeSelectedBlock(),
        {
            content: "Check that #wrap is empty",
            trigger: ":iframe #wrap:empty",
        },
        // Cover: test that parallax, bg-filter and shape are not treated as content
        ...insertSnippet({
            id: "s_cover",
            name: "Cover",
            groupName: "Intro",
        }),
        ...clickOnSnippet({
            id: "s_cover",
            name: "Cover",
        }),
        // Add a shape
        ...changeBackgroundShape(),
        {
            content: "Check that the parallax element is present",
            trigger: ":iframe #wrap .s_cover .s_parallax_bg",
        },
        {
            content: "Check that the filter element is present",
            trigger: ":iframe #wrap .s_cover .o_we_bg_filter",
        },
        {
            content: "Check that the shape element is present",
            trigger: ":iframe #wrap .s_cover .o_we_shape",
        },
        {
            content: "Check s_cover settings are loaded, wait for panel to be visible",
            trigger: ".o_customize_tab",
        },
        {
            content: "Click on the column",
            trigger: ":iframe #wrap .s_cover .row > :first-child",
            run: "click",
            // run: async (actions) => {
            //     // `shouldShowToolbar()` hides/shows the overlay buttons after
            //     // 500ms `setTimeout`. We add the same delay here to avoid a
            //     // race condition where the click fires before the overlay
            //     // buttons are visible.
            //     await delay(500);
            //     actions.click();
            // },
        },
        removeSelectedBlock(),
        {
            content: "Check that #wrap is empty",
            trigger: ":iframe #wrap:empty",
        },
    ]
);
