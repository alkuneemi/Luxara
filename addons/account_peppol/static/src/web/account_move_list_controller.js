import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { AlertDialog, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { AccountMoveListController } from "@account/views/account_move_list/account_move_list_controller";


patch(AccountMoveListController.prototype, {
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialogService = useService("dialog");
    },

    async _processAccountMovePeppolRecords(accountMoves) {
        const draftRecords = accountMoves.filter(rec => rec.state === 'draft');
        const postedRecords = accountMoves.filter(rec => rec.state !== 'cancel' && rec.state !== 'draft');

        await Promise.all([
            draftRecords.length && this.model.orm.call('account.move', 'action_peppol_cancel_and_remove_sequence', [draftRecords.map(rec => rec.id)]),
            postedRecords.length && this.model.orm.call('account.move', 'button_draft', [postedRecords.map(rec => rec.id)]),
        ]);
    },

    async onDeleteSelectedRecords() {
        const model = this.model.root.resModel;

        if (model === 'account.move') {
            const selectedRecords = this.model.root.selection;
            const selectedIds = selectedRecords.map(rec => rec.resId);

            const recordsData = await this.model.orm.read(
                'account.move',
                selectedIds,
                ['peppol_message_uuid', 'name', 'display_name', 'state']
            );

            const peppolRecords = recordsData.filter(rec => rec.peppol_message_uuid);

            if (peppolRecords.length > 0) {
                const peppolIdSet = new Set(peppolRecords.map(r => r.id));
                const regularIds = selectedIds.filter(id => !peppolIdSet.has(id));

                const cancelledPeppol = peppolRecords.filter(rec => rec.state === 'cancel');
                const draftPeppol = peppolRecords.filter(rec => rec.state === 'draft');
                const postedPeppol = peppolRecords.filter(rec => rec.state !== 'cancel' && rec.state !== 'draft');

                const processedCount = peppolRecords.length - cancelledPeppol.length;

                if (processedCount === 0 && regularIds.length === 0) {
                    this.dialogService.add(AlertDialog, {
                        title: _t("Cannot Delete"),
                        body: _t("Documents send/received via Peppol cannot be deleted."),
                        confirmLabel: _t("Close"),
                    });
                    return;
                }

                const label = rec => rec.name || rec.display_name;
                const sections = [];

                if (postedPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s Peppol document(s) will be reset to draft:\n\n• %s",
                        postedPeppol.length,
                        postedPeppol.map(label).join('\n• ')
                    ));
                }
                if (draftPeppol.length > 0) {
                    sections.push(_t(
                        "The following %s draft Peppol document(s) will be cancelled:\n\n• %s",
                        draftPeppol.length,
                        draftPeppol.map(label).join('\n• ')
                    ));
                }

                let message = sections.join('\n\n');

                if (regularIds.length > 0) {
                    message += _t("\n\nThe remaining %s document(s) will be deleted.", regularIds.length);
                }
                message += _t("\n\nDo you want to proceed?");

                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Peppol Documents Cannot Be Deleted"),
                    body: message,
                    confirm: async () => {
                        await this._processAccountMovePeppolRecords(peppolRecords);

                        if (regularIds.length > 0) {
                            await this.model.orm.unlink('account.move', regularIds);
                        }

                        this.notification.add(
                            _t(
                                "%(processed)s Peppol document(s) processed, %(deleted)s document(s) deleted",
                                { processed: processedCount, deleted: regularIds.length }
                            ),
                            { type: 'success' }
                        );

                        await this.model.root.load();
                        this.model.notify();
                    },
                    cancel: () => { },
                    confirmLabel: _t("Yes, Proceed"),
                    cancelLabel: _t("Cancel"),
                });

                return;
            }
        }

        return super.onDeleteSelectedRecords(...arguments);
    }
});
