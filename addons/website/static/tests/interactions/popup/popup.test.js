import { startInteractions, setupInteractionWhiteList } from "@web/../tests/public/helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    hover,
    leave,
    manuallyDispatchProgrammaticEvent,
    pointerDown,
    press,
    queryOne,
    tick,
} from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";

import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { defineStyle } from "@web/../tests/web_test_helpers";
import { startInteractionsWithSnippet } from "../helpers";
import { registry } from "@web/core/registry";

setupInteractionWhiteList("website.popup");

describe.current.tags("interaction_dev");

/**
 * Remove the CSS transitions because Bootstrap transitions don't work with Hoot.
 */
function removeTransitions() {
    defineStyle(/* css */ `
        * {
            transition: none !important;
        }
    `);
}

const modal = ".s_popup .modal";

const addPopupSnippetPreprocessor = ({
    showAfter = 0,
    display = "afterDelay",
    backdrop = true,
    extraPrimaryBtnClasses = "",
    modalId = "",
    focusableElements = false,
} = {}) => {
    registry
        .category("html_builder.snippetsPreprocessor")
        .add("test_snippets", function (namespace, snippets) {
            const popupEl = snippets.querySelector("[data-snippet='s_popup']");
            popupEl.id = "sPopup";
            const modalEl = popupEl.querySelector(".modal");
            modalEl.classList.toggle("s_popup_no_backdrop", !backdrop);
            modalEl.id = modalId;
            modalEl.dataset.showAfter = showAfter;
            modalEl.dataset.display = display;
            const primaryBtn = modalEl.querySelector(".btn-primary");
            if (extraPrimaryBtnClasses) {
                primaryBtn.classList.add(extraPrimaryBtnClasses);
            }
            if (focusableElements) {
                primaryBtn.insertAdjacentHTML("afterend", "<button id='focus'>Button 1</button>");
            }
        });
};

test("popup interaction does not activate without .s_popup", async () => {
    const { core } = await startInteractions(``);
    expect(core.interactions).toHaveLength(0);
});

describe("close popup", () => {
    beforeEach(removeTransitions);

    test("close popup with close button and check cookies", async () => {
        addPopupSnippetPreprocessor();
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        expect(cookie.get("sPopup")).not.toBe("true");
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await tick();
        await click(".js_close_popup");
        expect(modal).not.toBeVisible();
        expect(cookie.get("sPopup")).toBe("true");
    });

    test("close popup by pressing escape", async () => {
        addPopupSnippetPreprocessor();
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        // Focus the modal so that the escape is dispatched on the right element.
        await pointerDown(modal);
        await tick();
        await press("Escape");
        expect(modal).not.toBeVisible();
    });

    test("click on primary button closes popup", async () => {
        addPopupSnippetPreprocessor();
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await tick();
        await click(".btn-primary");
        expect(modal).not.toBeVisible();
    });

    test("click on primary button which is a form submit doesn't close popup", async () => {
        addPopupSnippetPreprocessor({ extraPrimaryBtnClasses: "o_website_form_send" });
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        expect(modal).toBeVisible();
        await click(".btn-primary.o_website_form_send");
        expect(modal).toBeVisible();
    });

    test("close popup by clicking outside the modal", async () => {
        addPopupSnippetPreprocessor();
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(modal).toBeVisible();
        await click(".modal");
        expect(modal).not.toBeVisible();
    });
});

describe("show popup", () => {
    beforeEach(removeTransitions);
    test("popup shows after 5000ms", async () => {
        addPopupSnippetPreprocessor({ showAfter: 5000 });
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        expect(modal).not.toBeVisible();
        await advanceTime(4500);
        expect(modal).not.toBeVisible();
        await advanceTime(1000);
        expect(modal).toBeVisible();
    });

    test("show popup after click on link", async () => {
        addPopupSnippetPreprocessor({ display: "onClick", modalId: "modal" });
        const processHTML = (html) => `<a href="#modal">Show popup</a>` + html;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        expect(core.interactions).toHaveLength(1);
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(modal).not.toBeVisible();
        await click("a[href='#modal']");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", {
            newURL: browser.location.hash,
        });
        expect(modal).toBeVisible();
    });

    test.tags("desktop");
    test("show popup when mouse leaves document", async () => {
        addPopupSnippetPreprocessor({ display: "mouseExit" });
        const { core } = await startInteractionsWithSnippet("s_popup");
        expect(core.interactions).toHaveLength(1);
        const modalEl = queryOne("#sPopup .modal");
        expect(modalEl).not.toBeVisible();
        await hover(modalEl.ownerDocument.body);
        await leave();
        expect(modalEl).toBeVisible();
    });
});

describe("trap focus", () => {
    beforeEach(removeTransitions);

    test("focus is trapped when popup opens", async () => {
        addPopupSnippetPreprocessor({ modalId: "modal", focusableElements: true });
        const processHTML = (html) => `<a href="#">Link</a>` + html;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
    });

    test("reset focus on the previous active element when popup is closed", async () => {
        addPopupSnippetPreprocessor({ modalId: "modal" });
        const processHTML = (html) => `<a id="showLink" href="#">Link</a>` + html;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("#showLink").toBeFocused();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await click(".s_popup_close");
        expect("#modal").not.toBeVisible();
        expect("#showLink").toBeFocused();
    });

    test("trap & reset focus when popup opens on click", async () => {
        addPopupSnippetPreprocessor({
            display: "onClick",
            modalId: "modal",
            focusableElements: true,
        });
        const processHTML = (html) => `<a href="#modal">Show popup</a>` + html;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        const modal = "#sPopup #modal[data-display='onClick']";
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("[href='#modal']").toBeFocused();
        await press("Enter");
        await manuallyDispatchProgrammaticEvent(window, "hashchange", {
            newURL: browser.location.hash,
        });
        expect(modal).toBeVisible();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
        await press("Escape");
        expect(modal).not.toBeVisible();
        expect("[href='#modal']").toBeFocused();
    });

    test("intercept & reset focus with no backdrop popup", async () => {
        addPopupSnippetPreprocessor({ modalId: "modal", backdrop: false });
        const processHTML = (html) => `<a id="link1" href="#">Link</a>` + html;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        expect(core.interactions).toHaveLength(1);
        await pointerDown(document.body);
        expect(document.body).toBeFocused(); // Just making sure.
        await press("Tab");
        expect("#link1").toBeFocused();
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Escape");
        expect("#link1").toBeFocused();
    });

    test("don't trap focus if no backdrop", async () => {
        addPopupSnippetPreprocessor({ modalId: "modal", backdrop: false, focusableElements: true });
        const processHTML = (html) => `
            <a id="link1" href="#">Link before</a>
            ${html}
            <a id="link2" href="#">Link after</a>
        `;
        const { core } = await startInteractionsWithSnippet("s_popup", { processHTML });
        expect(core.interactions).toHaveLength(1);
        await tick();
        await animationFrame();
        await advanceTime(100);
        expect("#modal").toBeVisible();
        await tick();
        expect(".btn-primary").toBeFocused();
        await press("Tab");
        expect("#focus").toBeFocused();
        await press("Tab");
        expect("#link2").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#focus").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect(".btn-primary").toBeFocused();
        await press("Tab", { shiftKey: true });
        expect("#link1").toBeFocused();
    });
});
