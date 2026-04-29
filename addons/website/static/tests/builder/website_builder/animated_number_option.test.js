import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { setSelection } from "@html_editor/../tests/_helpers/selection";
import { insertText } from "@html_editor/../tests/_helpers/user_actions";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("selecting part of the animated number selects the whole value", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilderWithSnippet(
        "s_animated_number"
    );
    const editable = getEditableContent();

    editable.querySelector(".s_animated_number_value strong").textContent = "1234";
    const displayEl = editable.querySelector(".s_animated_number_display");
    const textNode = editable.querySelector(".s_animated_number_value strong").firstChild;

    setSelection({ anchorNode: textNode, anchorOffset: 1, focusNode: textNode, focusOffset: 3 });
    await animationFrame();

    const selection = getEditor().shared.selection.getEditableSelection();
    expect(selection.textContent()).toBe("1234");
    expect(selection.startContainer).toBe(displayEl);
    expect(selection.startOffset).toBe(0);
    expect(selection.endContainer).toBe(displayEl);
    expect(selection.endOffset).toBe(1);
});

test("selecting the whole animated number does not change the selection", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilderWithSnippet(
        "s_animated_number"
    );
    const editable = getEditableContent();

    editable.querySelector(".s_animated_number_value strong").textContent = "1234";
    const textNode = editable.querySelector(".s_animated_number_value strong").firstChild;

    setSelection({ anchorNode: textNode, anchorOffset: 0, focusNode: textNode, focusOffset: 4 });
    await animationFrame();

    const selection = getEditor().shared.selection.getEditableSelection();
    expect(selection.textContent()).toBe("1234");
    expect(selection.startContainer).toBe(textNode);
    expect(selection.startOffset).toBe(0);
    expect(selection.endContainer).toBe(textNode);
    expect(selection.endOffset).toBe(4);
});

test("selecting across the animated number extends to the full value", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(`
        <div class="s_animated_number o_animable d-flex flex-column justify-content-center align-items-center"
            data-start-value="123"
            data-end-value="123"
            data-name="Animated Number"
        >
            <div class="s_animated_number_label">
                <h2>Clients</h2>
            </div>
            <div class="s_animated_number_display">
                <span class="s_animated_number_prefix">ab</span>
                <span class="s_animated_number_value"><span class="h2-fs"><strong>1234</strong></span></span>
                <span class="s_animated_number_postfix">d</span>
            </div>
        </div>
    `);
    const editable = getEditableContent();

    const displayEl = editable.querySelector(".s_animated_number_display");
    const prefixNode = editable.querySelector(".s_animated_number_prefix").firstChild;
    const textNode = editable.querySelector(".s_animated_number_value strong").firstChild;

    setSelection({ anchorNode: prefixNode, anchorOffset: 0, focusNode: textNode, focusOffset: 1 });
    await animationFrame();

    const selection = getEditor().shared.selection.getEditableSelection();
    expect(selection.textContent()).toBe("ab 1234");
    expect(selection.endContainer).toBe(displayEl);
    expect(selection.endOffset).toBe(4);
});

test("typing at the end of value prepends to existing postfix and keeps caret after inserted text", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(`
        <div class="s_animated_number o_animable d-flex flex-column justify-content-center align-items-center"
            data-start-value="1000"
            data-end-value="1000"
            data-name="Animated Number"
        >
            <div class="s_animated_number_display">
                <span class="s_animated_number_prefix"><span class="h2-fs"><strong>a</strong></span></span>
                <span class="s_animated_number_value"><span class="h2-fs"><strong>1000</strong></span></span>
                <span class="s_animated_number_postfix"><span class="h2-fs"><strong>bc</strong></span></span>
            </div>
        </div>
    `);
    const editable = getEditableContent();
    const editor = getEditor();

    const valueTextNode = editable.querySelector(".s_animated_number_value strong").firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: valueTextNode.length,
    });
    await insertText(editor, "de");
    await animationFrame();

    expect(editable.querySelector(".s_animated_number_value").textContent).toBe("1000");
    expect(editable.querySelector(".s_animated_number_postfix").textContent).toBe("debc");

    const selection = editor.shared.selection.getEditableSelection();
    const postfixTextNode = editable.querySelector(".s_animated_number_postfix strong").firstChild;
    expect(selection.isCollapsed).toBe(true);
    expect(selection.anchorNode).toBe(postfixTextNode);
    expect(selection.anchorOffset).toBe(2);
    expect(selection.focusNode).toBe(postfixTextNode);
    expect(selection.focusOffset).toBe(2);
});

test("typing a letter inside the number drops it", async () => {
    const { getEditableContent, getEditor } = await setupWebsiteBuilder(`
        <div class="s_animated_number o_animable d-flex flex-column justify-content-center align-items-center"
            data-start-value="1000"
            data-end-value="1000"
            data-name="Animated Number"
        >
            <div class="s_animated_number_display">
                <span class="s_animated_number_prefix"><span class="h2-fs"><strong>a</strong></span></span>
                <span class="s_animated_number_value"><span class="h2-fs"><strong>1000</strong></span></span>
                <span class="s_animated_number_postfix"><span class="h2-fs"><strong>bc</strong></span></span>
            </div>
        </div>
    `);
    const editable = getEditableContent();
    const editor = getEditor();

    const valueTextNode = editable.querySelector(".s_animated_number_value strong").firstChild;
    setSelection({
        anchorNode: valueTextNode,
        anchorOffset: 3,
    });
    await insertText(editor, "de");
    await animationFrame();

    expect(editable.querySelector(".s_animated_number_prefix").textContent).toBe("a");
    expect(editable.querySelector(".s_animated_number_value").textContent).toBe("1000");
    expect(editable.querySelector(".s_animated_number_postfix").textContent).toBe("bc");
});
