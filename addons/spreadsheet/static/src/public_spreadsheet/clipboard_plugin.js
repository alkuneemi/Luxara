import { CommandResult, UIPlugin, registries } from "@odoo/o-spreadsheet";

const { statefulUIPluginRegistry } = registries;

class ClipboardPlugin extends UIPlugin {
    allowDispatch(cmd) {
        if (cmd.type === "COPY" && this.getters.getSelectedFigureId()) {
            return CommandResult.Readonly;
        }
        return CommandResult.Success;
    }
}

statefulUIPluginRegistry.add("public_clipboard", ClipboardPlugin);
