import {
    addBuilderOption,
    addBuilderPlugin,
    setupHTMLBuilder,
} from "@html_builder/../tests/helpers";
import { Plugin } from "@html_editor/plugin";
import { expect, test } from "@odoo/hoot";
import { xml } from "@odoo/owl";
import { contains } from "@web/../tests/web_test_helpers";

test("Should show anchor button based on resource selectors", async () => {
    class TestPlugin extends Plugin {
        static id = "test";
        resources = {
            anchor_allowed_selectors: ".allowed",
            anchor_excluded_selectors: ".excluded, .force-allowed",
            anchor_force_allowed_selectors: ".force-allowed",
        };
    }
    addBuilderPlugin(TestPlugin);
    addBuilderOption({
        selector: ".allowed, .excluded, .force-allowed",
        template: xml`<BuilderButton classAction="'test'">Test</BuilderButton>`,
    });
    await setupHTMLBuilder(`
            <div data-name="Link creation allowed" class="allowed">
                Allowed link to be created
            </div>
            <div data-name="Link creation not allowed" class="excluded">
                Not allowed link to be created
            </div>
            <div data-name="Link creation force allowed" class="force-allowed">
                Force allowed link to be created
            </div>
        `);

    await contains(":iframe .allowed").click();
    expect(".options-container .oe_snippet_anchor").toHaveCount(1);

    await contains(":iframe .excluded").click();
    expect(".options-container .oe_snippet_anchor").toHaveCount(0);

    await contains(":iframe .force-allowed").click();
    expect(".options-container .oe_snippet_anchor").toHaveCount(1);
});
