/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListController } from "@web/views/list/list_controller";

export class AccountJournalListController extends ListController {
    setup() {
        super.setup();
        // Explicitly hide the "New" button from the list UI
        this.activeActions.create = false;
    }
}

export const accountJournalListView = {
    ...listView,
    Controller: AccountJournalListController,
};

registry.category("views").add("account_journal_list", accountJournalListView);
