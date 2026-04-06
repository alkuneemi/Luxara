import { expect, test } from "@odoo/hoot";
import { contains, defineModels, fields, models } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilderWithSnippet,
} from "@website/../tests/builder/website_helpers";

class MailingList extends models.Model {
    name = fields.Char();
    is_public = fields.Boolean({ default: true });
    _records = [{ id: 1, name: "Newsletter List", is_public: true }];
}

defineWebsiteModels();
defineModels({ MailingList });

test("Options related to newsletter form should be at the form level", async () => {
    await setupWebsiteBuilderWithSnippet("s_newsletter_block");
    await contains(":iframe .s_newsletter_subscribe_form").click();
    expect("[data-container-title='Newsletter Form'] [data-label='On Success']").toHaveCount(1);
    await contains("[data-label='On Success'] [data-action-id='toggleThanksMessage']").click();
    expect(":iframe .js_subscribe .js_subscribed_wrap.o_enable_preview").toHaveCount(1);
    expect(":iframe .js_subscribe .js_subscribe_wrap.o_disable_preview").toHaveCount(1);
    expect(":iframe .js_subscribe .js_subscribed_wrap p").toHaveClass("mb-0");
});
