import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import {
    animationFrame,
    beforeEach,
    describe,
    edit,
    expect,
    mockDate,
    press,
    test,
} from "@odoo/hoot";
import { setupEditor } from "./_helpers/editor";
import { insertText, simulateArrowKeyPress } from "./_helpers/user_actions";
import {
    contains,
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { expectElementCount } from "./_helpers/ui_expectations";
import { getContent } from "./_helpers/selection";

const { DateTime } = luxon;

const configWithEmbeddings = {
    Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

beforeEach(() => {
    patchWithCleanup(user, { tz: "Europe/Brussels" });
    mockDate("2026-04-05T20:45:00");
});

describe("date command", () => {
    test('"/today" command inserts the current date', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/today");
        await animationFrame();
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("April 5, 2026");
    });

    test.tags("desktop");
    test('"/hour" command inserts the current time', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/hour");
        await animationFrame();
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("10:45 PM");

        // Edit inserted time
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_time_picker", 1);
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(16:00)").click();
        await expectElementCount(".o_time_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");
    });

    test.tags("mobile");
    test("should be able to edit time using timepicker", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/hour");
        await animationFrame();
        await press("Enter");
        expect('[data-embedded="date"]').toHaveCount(1);
        await animationFrame();
        expect('[data-embedded="date"] span').toHaveText("10:45 PM");

        // Edit inserted time
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_time_picker", 1);
        await edit("16:00");
        await expectElementCount(".o_time_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("4:00 PM");
    });
    test('"/date" command opens a date picker', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/insertdate");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('7')").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("April 7, 2026");

        // Edit inserted date
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('6')").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("April 6, 2026");
    });

    test.tags("desktop");
    test('"/datetime" command opens a datetime picker', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_datetime_picker button[title='Clear']").toHaveCount(0);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_date_item_cell:contains('7')").click();
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(10:30)").click();
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 7, 2026, 10:30 AM");

        // Edit inserted date
        await contains('[data-embedded="date"] span').click();
        await expectElementCount(".o_datetime_picker", 1);
        await contains(".o_date_item_cell:contains('6')").click();
        await contains(".o_time_picker input").click();
        await contains(".o_time_picker_option:contains(16:30)").click();
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"] span').toHaveText("Apr 6, 2026, 4:30 PM");
    });

    test.tags("mobile");
    test('"/datetime" command opens a datetime picker in mobile', async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_date_item_cell:contains('7')").click();
        await contains(".o_time_picker input").click();
        await edit("10:30");
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 7, 2026, 10:30 AM");
    });
    test("date should get updated according to the timezone", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", {
            config: configWithEmbeddings,
        });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 5, 2026, 10:45 PM");
        await press("Backspace");

        // Change timezone
        patchWithCleanup(user, { tz: "Asia/Kolkata" });
        await insertText(editor, "/datetime");
        await animationFrame();
        await press("Enter");
        await expectElementCount(".o_datetime_picker", 1);
        expect(".o_time_picker").toHaveCount(1);
        await contains(".o_datetime_buttons button").click();
        await expectElementCount(".o_datetime_picker", 0);
        expect('[data-embedded="date"]').toHaveCount(1);
        expect('[data-embedded="date"] span').toHaveText("Apr 6, 2026, 2:15 AM");
    });
    test("Embedded date component should work in readonly mode", async () => {
        class Test extends models.Model {
            name = fields.Char();
            txt = fields.Html();
            _records = [
                {
                    id: 1,
                    name: "Test",
                    txt: `<div class="o-paragraph"><span data-embedded="date" data-embedded-props='{"date":"${DateTime.now()
                        .toUTC()
                        .toISO()}","type":"date"}' data-oe-protected="true" contenteditable="false"></div>`,
                },
            ];
        }

        defineModels([Test]);
        await mountView({
            type: "form",
            resId: 1,
            resModel: "test",
            arch: `
                <form>
                    <field name="name"/>
                    <field name="txt" widget="html" readonly="1" options="{'embedded_components': True}"/>
                </form>`,
        });
        expect(`[name="txt"] .o_readonly`).toHaveCount(1);
        expect(`[name="txt"] .o_readonly [data-embedded="date"]`).toHaveInnerHTML(
            `<span class="oe-date-pill">April 5, 2026</span>`
        );
    });
    test("should navigate correctly around embedded date components", async () => {
        const dateUTC = DateTime.now().toUTC().toISO();
        const { el, editor } = await setupEditor(
            `<p>abc</p><p><span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span></p><p>def<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}'></span>[]</p>`,
            {
                config: configWithEmbeddings,
            }
        );
        const embeddedDate = `<span data-embedded="date" data-embedded-props='{"date":"${dateUTC}","type":"date"}' data-oe-protected="true" contenteditable="false"><span class="oe-date-pill cursor-pointer">April 5, 2026</span></span>`;
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}\uFEFF[]</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowUp");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF[]</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowUp");
        expect(getContent(el)).toBe(
            `<p>abc[]</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowDown");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF[]</p><p>def\uFEFF${embeddedDate}\uFEFF</p>`
        );

        await simulateArrowKeyPress(editor, "ArrowDown");
        expect(getContent(el)).toBe(
            `<p>abc</p><p>\uFEFF${embeddedDate}\uFEFF</p><p>def\uFEFF${embeddedDate}[]\uFEFF</p>`
        );
    });
});
