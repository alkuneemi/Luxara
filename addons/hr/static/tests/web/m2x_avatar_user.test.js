import { describe, expect, test } from "@odoo/hoot";
import { queryAllTexts, waitFor } from "@odoo/hoot-dom";
import { contains, makeMockServer, mountView } from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";
import { click as mailClick, contains as mailContains } from "@mail/../tests/mail_test_helpers";
import { defineHrModels } from "@hr/../tests/hr_test_helpers";

describe.current.tags("desktop");
defineHrModels();

test("avatar card preview with hr", async () => {
    const { env } = await makeMockServer();
    const departmentId = env["hr.department"].create({
        name: "Management",
        complete_name: "Management",
    });
    const partnerId = env["res.partner"].create({
        name: "Mario",
        email: "Mario@odoo.test",
        phone: "+7878698799",
    });
    const jobId = env["hr.job"].create({
        name: "sub manager",
    });
    const workLocationId = env["hr.work.location"].create({
        name: "Odoo",
        location_type: "office",
    });
    const versionId = env["hr.version"].create({
        job_id: jobId,
        work_location_id: workLocationId,
        department_id: departmentId,
    });
    const employeeId = env["hr.employee"].create({
        version_id: versionId,
        work_email: "Mario@odoo.pro",
        work_location_type: "office",
        work_phone: "+585555555",
    });
    const userId = env["res.users"].create({
        partner_id: partnerId,
        im_status: "online",
        employee_id: employeeId,
        employee_ids: [employeeId],
    });
    env["hr.employee"].write(employeeId, {
        user_id: userId,
        work_contact_id: partnerId,
    });
    env["m2x.avatar.user"].create({ user_id: userId });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="user_id" widget="many2one_avatar_user"/>
                </t>
            </templates>
        </kanban>`,
    });
    await contains(".o_m2o_avatar > img").click();
    await mailContains(".o_avatar_card");
    await mailContains(".o_avatar_card span[data-tooltip='Work Location'] .fa-building-o");
    expect(queryAllTexts(".o_card_user_infos > *:not(.o_avatar_card_buttons)")).toEqual([
        "Mario",
        "Management",
        "Mario@odoo.pro",
        "+585555555",
        "Odoo",
    ]);
    await contains(".o_action_manager:eq(0)").click();
    await mailContains(".o_avatar_card", { count: 0 });
});

test("avatar card preview with hr (partner_id field)", async () => {
    const { env } = await makeMockServer();
    const departmentId = env["hr.department"].create({
        name: "Management",
        complete_name: "Management",
    });
    const partnerId = env["res.partner"].create({
        name: "Mario",
        email: "Mario@odoo.test",
        phone: "+7878698799",
    });
    const jobId = env["hr.job"].create({
        name: "sub manager",
    });
    const workLocationId = env["hr.work.location"].create({
        name: "Odoo",
        location_type: "office",
    });
    const versionId = env["hr.version"].create({
        job_id: jobId,
        work_location_id: workLocationId,
        department_id: departmentId,
    });
    const employeeId = env["hr.employee"].create({
        version_id: versionId,
        work_email: "Mario@odoo.pro",
        work_location_type: "office",
        work_phone: "+585555555",
    });
    env["hr.employee"].write(employeeId, {
        work_contact_id: partnerId,
    });
    env["m2x.avatar.user"].create({ partner_id: partnerId });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="partner_id" widget="many2one_avatar_user"/>
                </t>
            </templates>
        </kanban>`,
    });
    await contains(".o_m2o_avatar > img").click();
    await mailContains(".o_avatar_card");
    await mailContains(".o_avatar_card span[data-tooltip='Work Location'] .fa-building-o");
    expect(queryAllTexts(".o_card_user_infos > *:not(.o_avatar_card_buttons)")).toEqual([
        "Mario",
        "Management",
        "Mario@odoo.pro",
        "+585555555",
        "Odoo",
    ]);
    await contains(".o_action_manager:eq(0)").click();
    await mailContains(".o_avatar_card", { count: 0 });
});

test("employees with user prioritized over employees without user", async () => {
    const { env } = await makeMockServer();
    const partnerId = env["res.partner"].create({ name: "John" });
    const userId = env["res.users"].create({ partner_id: partnerId });
    const otherCompanyId = env["res.company"].create({ name: "Other Company" });
    const [department1Id, department2Id] = env["hr.department"].create([
        { name: "RD Discuss" },
        { name: "RD Livechat" },
    ]);
    env["hr.employee"].create([
        {
            department_id: department1Id,
            work_contact_id: partnerId,
            user_id: userId,
            company_id: user.activeCompany.id,
        },
        {
            department_id: department2Id,
            work_contact_id: partnerId,
            user_id: userId,
            company_id: otherCompanyId,
        },
        {
            department_id: department2Id,
            work_contact_id: partnerId,
            company_id: user.activeCompany.id,
        },
        {
            department_id: department2Id,
            work_contact_id: partnerId,
            company_id: user.activeCompany.id,
            active: false,
        },
    ]);
    env["m2x.avatar.user"].create({ partner_id: partnerId });
    await mountView({
        type: "kanban",
        resModel: "m2x.avatar.user",
        arch: `<kanban>
            <templates>
                <t t-name="card">
                    <field name="partner_id" widget="many2one_avatar_user"/>
                </t>
            </templates>
        </kanban>`,
    });
    await mailClick(".o_m2o_avatar > img");
    await waitFor(".o-mail-avatar-card-name");
    await mailContains(".o_card_user_infos > span:contains('John')");
    await mailContains(".o_card_user_infos > span:contains('RD Discuss')");
    await mailClick(".o_action_manager:eq(0)");
    await waitFor(".o_avatar_card");
});
