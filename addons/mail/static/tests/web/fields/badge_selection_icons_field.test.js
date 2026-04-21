import { expect, test } from "@odoo/hoot";
import { defineModels, fields, models, mountView, onRpc } from "@web/../tests/web_test_helpers";

class MailActivityType extends models.Model {
    _name = "mail.activity.type";

    icon = fields.Char();

    _records = [
        { id: 1, name: "Email", icon: "fa-envelope" },
        { id: 2, name: "Call", icon: "fa-phone" },
        { id: 28, name: "Upload Document", icon: "fa-upload" },
    ];
}

class WorkLocation extends models.Model {
    _name = "work.location";

    location_type = fields.Char();

    _records = [
        { id: 1, name: "Home", location_type: "home" },
        { id: 2, name: "Office", location_type: "office" },
        { id: 3, name: "Other", location_type: "other" },
    ];
}

class Foo extends models.Model {
    _name = "foo";

    activity_type_id = fields.Many2one({ relation: "mail.activity.type" });
    work_location_id = fields.Many2one({ relation: "work.location" });

    _records = [{ id: 1 }];
}

defineModels([Foo, MailActivityType, WorkLocation]);
onRpc("has_group", () => true);

test("selection_badge_icons widget renders icons from related many2one field", async () => {
    await mountView({
        resModel: "foo",
        resId: 1,
        type: "form",
        arch: `<form>
            <field name="activity_type_id"
                widget="selection_badge_icons"
                options="{'related_icon_field': 'icon'}"/>
        </form>`,
    });
    expect(".o_selection_badge span.fa-envelope").toHaveCount(1);
    expect(".o_selection_badge span.fa-phone").toHaveCount(1);
    expect(".o_selection_badge span.fa-upload").toHaveCount(1);
});

test("selection_badge_icons widget falls back to default icon when value missing from icon_mapping", async () => {
    await mountView({
        resModel: "foo",
        resId: 1,
        type: "form",
        arch: `<form>
            <field name="work_location_id"
                widget="selection_badge_icons"
                options="{
                    'icon_mapping': {'office': 'fa-building-o', 'home': 'fa-home'},
                    'related_icon_field': 'location_type',
                    'default_icon': 'fa-map-marker'
                }"/>
        </form>`,
    });
    expect(".o_selection_badge span.fa-home").toHaveCount(1);
    expect(".o_selection_badge span.fa-building-o").toHaveCount(1);
    expect(".o_selection_badge span.fa-map-marker").toHaveCount(1);
    expect(".o_selection_badge span.other").toHaveCount(0);
});
