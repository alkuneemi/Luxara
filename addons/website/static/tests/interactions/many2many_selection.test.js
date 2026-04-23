import { describe, expect, test } from "@odoo/hoot";
import { queryAll, queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

setupInteractionWhiteList(["website.many2many_selection", "website.form"]);

describe.current.tags("interaction_dev");

function getMany2MSelectionHtml() {
    return `
        <section class="s_website_form">
            <form action="/website/form/" method="post" enctype="multipart/form-data" data-model_name="mail.mail">
                <div class="s_website_form_m2m_selection dropdown">
                    <select multiple="multiple" class="s_website_form_input d-none" name="m2m_field">
                        <option value="1" selected="selected">One</option>
                        <option value="2">Two</option>
                    </select>
                    <button id="m2m_sel" class="s_website_form_m2m_pills_container form-select d-flex flex-wrap" type="button" aria-haspopup="listbox" data-bs-toggle="dropdown" data-bs-auto-close="outside">
                        <span class="s_website_form_m2m_placeholder d-none">Pick</span>
                        <span class="s_website_form_m2m_pill badge rounded-pill text-bg-primary" data-value="1">
                            <span>One</span>
                            <i class="fa fa-times cursor-pointer"></i>
                        </span>
                        <span class="s_website_form_m2m_pill badge rounded-pill text-bg-primary d-none" data-value="2">
                            <span>Two</span>
                            <i class="fa fa-times cursor-pointer"></i>
                        </span>
                    </button>
                    <div class="dropdown-menu w-100">
                        <button type="button" class="dropdown-item cursor-pointer" data-value="1">
                            <input tabindex="-1" type="checkbox" class="form-check-input" checked="checked"/>
                            <span>One</span>
                        </button>
                        <button type="button" class="dropdown-item cursor-pointer" data-value="2">
                            <input tabindex="-1" type="checkbox" class="form-check-input"/>
                            <span>Two</span>
                        </button>
                    </div>
                </div>
                <div class="s_website_form_submit" data-name="Submit Button">
                    <span id="s_website_form_result"></span>
                    <a href="#" role="button" class="btn btn-primary s_website_form_send">Submit</a>
                </div>
            </form>
        </section>`;
}

const VISIBLE_PILL = ".s_website_form_m2m_pill:not(.d-none)";

test("initial state reflects pre-selected options", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    const selectEl = queryOne("select.s_website_form_input");
    const checkbox1El = queryOne(".dropdown-item[data-value='1'] input[type=checkbox]");
    const checkbox2El = queryOne(".dropdown-item[data-value='2'] input[type=checkbox]");

    expect(selectEl.querySelector("option[value='1']").selected).toBe(true);
    expect(checkbox1El.checked).toBe(true);
    expect(selectEl.querySelector("option[value='2']").selected).toBe(false);
    expect(checkbox2El.checked).toBe(false);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(1);
});

test("clicking a dropdown option selects it and shows the matching pill", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    await contains(".s_website_form_m2m_pills_container").click();
    await contains(".dropdown-item[data-value='2']").click();

    expect(queryOne("select.s_website_form_input option[value='2']").selected).toBe(true);
    expect(queryOne(".dropdown-item[data-value='2'] input[type=checkbox]").checked).toBe(true);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(2);
});

test("clicking a selected dropdown option deselects it and hides the pill", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    await contains(".s_website_form_m2m_pills_container").click();
    await contains(".dropdown-item[data-value='1']").click();

    expect(queryOne("select.s_website_form_input option[value='1']").selected).toBe(false);
    expect(queryOne(".dropdown-item[data-value='1'] input[type=checkbox]").checked).toBe(false);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(0);
});

test("clicking a pill's remove button deselects the option and hides the pill", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    await contains(".s_website_form_m2m_pill i").click();

    expect(queryOne("select.s_website_form_input option[value='1']").selected).toBe(false);
    expect(queryOne(".dropdown-item[data-value='1'] input[type=checkbox]").checked).toBe(false);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(0);
});

test("placeholder is hidden when pills are present and shown when none remain", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    const placeholderEl = queryOne(".s_website_form_m2m_placeholder");

    expect(placeholderEl).toHaveClass("d-none");

    await contains(".s_website_form_m2m_pill i").click();
    expect(placeholderEl).not.toHaveClass("d-none");
});

test("cleanup restores initial selected state", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    await contains(".s_website_form_m2m_pills_container").click();
    await contains(".dropdown-item[data-value='2']").click();
    await contains(".dropdown-item[data-value='1']").click();

    const selectEl = queryOne("select.s_website_form_input");
    expect(selectEl.querySelector("option[value='1']").selected).toBe(false);
    expect(selectEl.querySelector("option[value='2']").selected).toBe(true);

    core.stopInteractions();

    expect(selectEl.querySelector("option[value='1']").selected).toBe(true);
    expect(selectEl.querySelector("option[value='2']").selected).toBe(false);
    expect(queryAll(VISIBLE_PILL)).toHaveLength(1);
    expect(queryOne(".dropdown-item[data-value='1'] input[type=checkbox]").checked).toBe(true);
    expect(queryOne(".dropdown-item[data-value='2'] input[type=checkbox]").checked).toBe(false);
});

test("form sends the selected pills values on submit", async () => {
    const { core } = await startInteractions(getMany2MSelectionHtml());
    expect(core.interactions).toHaveLength(2);

    await contains(".s_website_form_m2m_pills_container").click();
    await contains(".dropdown-item[data-value='2']").click();

    onRpc("/website/form/mail.mail", async (request) => {
        const formData = await request.formData();
        expect(formData.getAll("m2m_field")).toEqual(["1,2"]);
        expect.step("submitted");
    });

    await contains(".s_website_form_send").click();
    expect.verifySteps(["submitted"]);
});
