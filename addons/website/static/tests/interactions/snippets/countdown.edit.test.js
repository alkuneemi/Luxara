import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";
import { startInteractionsWithSnippet } from "../helpers";
import { tick } from "@odoo/hoot-dom";
import { addCountdownSnippetPreprocessor } from "./helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.countdown");

test("past date: end message is not shown and countdown remains visible", async () => {
    addCountdownSnippetPreprocessor({ endAction: "message_no_countdown", endTime: 1 });
    const { core } = await startInteractionsWithSnippet("s_countdown", {
        waitForStart: true,
        editMode: true,
    });
    await switchToEditMode(core);

    await tick();
    expect(".s_countdown_end_message:not(.d-none)").toHaveCount(0);
    expect(".s_countdown_canvas_flex canvas:not(.d-none)").toHaveCount(4);
});
