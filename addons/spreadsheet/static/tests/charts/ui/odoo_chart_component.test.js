import { animationFrame } from "@odoo/hoot-mock";
import { expect, test, beforeEach } from "@odoo/hoot";
import { getBasicData, defineSpreadsheetModels } from "@spreadsheet/../tests/helpers/data";
import { createBasicChart, updateChart } from "@spreadsheet/../tests/helpers/commands";
import { mountSpreadsheet } from "@spreadsheet/../tests/helpers/ui";
import { createModelWithDataSource } from "@spreadsheet/../tests/helpers/model";
import { serverState } from "@web/../tests/web_test_helpers";

defineSpreadsheetModels();

/**
 * @typedef {import("@spreadsheet/../tests/helpers/data").ServerData} ServerData
 */

const chartId = "uuid1";
let serverData = /** @type {ServerData} */ ({});

beforeEach(() => {
    serverData = {};
    serverData.menus = {
        1: {
            id: 1,
            name: "test menu 1",
            xmlid: "spreadsheet.test.menu",
            appID: 1,
            actionID: "menuAction",
        },
        2: {
            id: 2,
            name: "test menu 2",
            xmlid: "spreadsheet.test.menu2",
            appID: 1,
            actionID: "menuAction2",
        },
        3: {
            id: 3,
            name: "test menu 2",
            xmlid: "spreadsheet.test.menu_without_action",
            appID: 1,
        },
    };
    serverData.actions = {
        menuAction: {
            id: 99,
            xml_id: "menuAction",
            name: "menuAction",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
        menuAction2: {
            id: 100,
            xml_id: "menuAction2",
            name: "menuAction2",
            res_model: "ir.ui.menu",
            type: "ir.actions.act_window",
            views: [[false, "list"]],
        },
    };
    serverData.models = {
        ...getBasicData(),
        "ir.ui.menu": {
            records: [
                { id: 1, name: "test menu 1", action: "action1", group_ids: [10] },
                { id: 2, name: "test menu 2", action: "action2", group_ids: [10] },
            ],
        },
        "res.group": { records: [{ id: 10, name: "test group" }] },
        "res.users": {
            records: [{ id: 1, active: true, partner_id: serverState.partnerId, name: "Raoul" }],
        },
        "ir.actions": { records: [{ id: 1 }] },
    };
    serverState.userId = 1;
});

test("icon external link isn't on the chart when its not linked to an odoo menu", async function () {
    const { model } = await createModelWithDataSource({
        serverData,
    });
    const fixture = await mountSpreadsheet(model);
    createBasicChart(model, chartId);
    updateChart(model, chartId, {
        annotationText: "test",
    });
    await animationFrame();
    const infoIcon = fixture.querySelector(".o-chart-item[data-id='chartInfo']");
    expect(infoIcon).not.toBe(null);
});
