import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { firstLeaf } from "@html_editor/utils/dom_traversal";
import { boundariesOut } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { ClassAction } from "@html_builder/core/core_builder_action_plugin";
import { _t } from "@web/core/l10n/translation";

class AnimatedNumberOptionPlugin extends Plugin {
    static id = "animatedNumberOption";
    static dependencies = ["selection"];

    /** @type {import("plugins").WebsiteResources} */
    resources = {
        so_content_addition_selectors: [".s_animated_number"],
        is_unremovable_selectors: ".s_animated_number_display, .s_animated_number_value",
        builder_actions: {
            ToggleTitleAnimatedNumberAction,
        },
        on_selectionchange_handlers: withSequence(-1, this.onSelectionChange.bind(this)),
        normalize_processors: this.normalize.bind(this),
        clean_for_save_processors: this.cleanForSave.bind(this),
    };

    onSelectionChange(selectionData) {
        if (
            !selectionData.documentSelectionIsInEditable ||
            selectionData.editableSelection.isCollapsed
        ) {
            return;
        }

        const selection = selectionData.editableSelection;
        const numberEl = [...this.editable.querySelectorAll(".s_animated_number_value")].find(
            (el) => selection.intersectsNode(el)
        );
        if (!numberEl) {
            return;
        }

        const numberLeaf = firstLeaf(numberEl);
        if (!numberLeaf || numberLeaf.nodeType !== Node.TEXT_NODE) {
            return;
        }

        const [startNode, startOffset, endNode, endOffset] = boundariesOut(numberEl);
        const snapStart =
            selection.startContainer === numberLeaf &&
            selection.startOffset > 0 &&
            selection.startOffset < numberLeaf.length;
        const snapEnd =
            selection.endContainer === numberLeaf &&
            selection.endOffset > 0 &&
            selection.endOffset < numberLeaf.length;
        if (!snapStart && !snapEnd) {
            return;
        }

        const start = snapStart
            ? [startNode, startOffset]
            : [selection.startContainer, selection.startOffset];
        const end = snapEnd ? [endNode, endOffset] : [selection.endContainer, selection.endOffset];
        const [anchorNode, anchorOffset] = selection.direction ? start : end;
        const [focusNode, focusOffset] = selection.direction ? end : start;
        this.dependencies.selection.setSelection(
            { anchorNode, anchorOffset, focusNode, focusOffset },
            { normalize: false }
        );
    }

    cleanForSave(root) {
        for (const el of root.querySelectorAll(".s_animated_number")) {
            let numberEl = el.querySelector(".s_animated_number_value");
            if (!numberEl) {
                // If no .s_animated_number_value element is found, restore it
                // to default to fix the snippet
                numberEl = this.document.createElement("span");
                numberEl.classList.add("s_animated_number_value");
                const fontSizeEl = this.document.createElement("span");
                fontSizeEl.classList.add("h2-fs");
                const fontWeightEl = this.document.createElement("strong");
                fontSizeEl.append(fontWeightEl);
                numberEl.append(fontSizeEl);
                el.querySelector(".s_animated_number_display").replaceChildren(numberEl);
                continue;
            }
            numberEl = firstLeaf(numberEl, (el) => el.childNodes.length != 1);
            numberEl.textContent = el.dataset.startValue || 0;
        }
        for (const el of root.querySelectorAll(
            ".s_animated_number_prefix, .s_animated_number_postfix"
        )) {
            if (el.textContent == "") {
                el.remove();
            }
        }
    }

    normalize(root) {
        console.log("normalize");
        const displayEl = root.closest(".s_animated_number_display");
        if (!displayEl) {
            return;
        }

        const valueEl = displayEl.querySelector(".s_animated_number_value");
        if (!valueEl) {
            return;
        }

        const textContent = valueEl.textContent;
        const valueTextNode = firstLeaf(valueEl, (el) => el.childNodes.length != 1);
        const selection = this.dependencies.selection.getEditableSelection();
        const digits = (textContent.match(/\d/g) || []).join("");
        if (!digits) {
            firstLeaf(valueEl).textContent = "0";
            return;
        }
        const firstDigitIndex = textContent.search(/\d/);
        let lastDigitIndex = -1;
        for (let index = textContent.length - 1; index >= 0; --index) {
            if (/\d/.test(textContent[index])) {
                lastDigitIndex = index;
                break;
            }
        }
        const prefix = textContent.slice(0, firstDigitIndex);
        const postfix = textContent.slice(lastDigitIndex + 1);
        const number = digits;
        const shouldRestoreCursorToPostfix =
            selection?.isCollapsed &&
            selection.anchorNode === valueTextNode &&
            selection.anchorOffset === valueTextNode.length &&
            postfix.length > 0;

        if (prefix) {
            let prefixEl = displayEl.querySelector(".s_animated_number_prefix");
            if (!displayEl.querySelector(".s_animated_number_prefix")) {
                prefixEl = valueEl.cloneNode(true);
                prefixEl.classList = "s_animated_number_prefix";
                valueEl.insertAdjacentElement("beforebegin", prefixEl);
            }
            if (prefixEl.textContent != prefix) {
                firstLeaf(prefixEl).textContent = prefix;
            }
        }

        if (postfix) {
            let postfixEl = displayEl.querySelector(".s_animated_number_postfix");
            if (!displayEl.querySelector(".s_animated_number_postfix")) {
                postfixEl = valueEl.cloneNode(true);
                postfixEl.classList = "s_animated_number_postfix";
                valueEl.insertAdjacentElement("afterend", postfixEl);
                firstLeaf(postfixEl).textContent = postfix;
            } else {
                const postfixTextNode = firstLeaf(postfixEl, (el) => el.childNodes.length != 1);
                postfixTextNode.textContent = `${postfix}${postfixTextNode.textContent}`;
            }
        }

        if (textContent != number) {
            firstLeaf(valueEl).textContent = number;
        }

        if (shouldRestoreCursorToPostfix) {
            const postfixEl = displayEl.querySelector(".s_animated_number_postfix");
            const postfixTextNode =
                postfixEl && firstLeaf(postfixEl, (el) => el.childNodes.length != 1);
            if (postfixTextNode) {
                this.dependencies.selection.setSelection({
                    anchorNode: postfixTextNode,
                    anchorOffset: Math.min(postfix.length, postfixTextNode.length),
                });
            }
        }
    }
}

export class ToggleTitleAnimatedNumberAction extends ClassAction {
    static id = "toggleTitleAnimatedNumber";

    isApplied({ editingElement, value }) {
        if (!value) {
            return !editingElement.querySelector(".s_animated_number_label");
        } else {
            return true;
        }
    }
    apply({ editingElement, value }) {
        if (!value) {
            editingElement.querySelector(".s_animated_number_label")?.remove();
        } else if (!editingElement.querySelector(".s_animated_number_label")) {
            const titleEl = document.createElement("div");
            titleEl.classList.add(
                "s_animated_number_label",
                "d-flex",
                "justify-content-center",
                "align-items-center"
            );
            const h2El = document.createElement("h2");
            h2El.textContent = _t("Clients");
            titleEl.append(h2El);
            editingElement.prepend(titleEl);
        }
    }
}

registry.category("website-plugins").add(AnimatedNumberOptionPlugin.id, AnimatedNumberOptionPlugin);
