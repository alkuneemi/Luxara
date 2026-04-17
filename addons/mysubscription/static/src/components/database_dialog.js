import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useState } from "@web/owl2/utils";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class DatabaseDialog extends Component {
    static components = { Dialog };
    static template = "mysubscription.DatabaseDialog";
    static props = {
        action: { type: String }, // rename, duplicate, backup, drop
        dbName: { type: String },
        close: { type: Function },
    };

    setup() {
        this.notification = useService("notification");
        this.dialog = useService("dialog");

        const timestamp = DateTime.now().toFormat("yyyy-MM-dd_HH-mm-ss");

        this.state = useState({
            isProcessing: false,
            masterPwd: "",
            duplicateName: "",
            duplicateNeutralize: true,
            backupFilename: `${this.props.dbName}_${timestamp}`,
            backupFormat: "zip",
        });
    }

    get title() {
        const titles = {
            backup: "Download Database Backup",
            duplicate: "Duplicate Database",
            rename: "Rename Database",
            drop: "Delete Database",
        }
        // if (!(this.props.action in titles)) {
        //     throw "Val";
        // }
        return titles[this.props.action];
    }

    get formData() {
        /*
        - backup HTTP:    master_pwd, name, backup_format='zip', filestore=True
        - duplicate HTTP: master_pwd, name, new_name, neutralize_database=False
        - drop HTTP:      master_pwd, name
        - rename HTTP:    master_pwd, name, new_name --> (duplicate + drop)
        */
        const formData = new FormData();

        formData.append("master_pwd", this.state.masterPwd);
        formData.append("name", this.props.dbName);

        switch (this.props.action) {
            case "backup":
                formData.append("backup_format", this.state.backupFormat);
                formData.append("filestore", true);
                break;
            case "duplicate":
                formData.append("new_name", this.state.duplicateName);
                formData.append("neutralize_database", this.state.duplicateNeutralize);
                break;
            case "rename":
                formData.append("new_name", this.state.duplicateName);
                formData.append("neutralize_database", false);
        }
        return formData;
    }

    async onBackupBeforeDrop() {
        this.dialog.add(DatabaseDialog, {
            action: "backup",
            dbName: this.props.dbName,
        })
    }

    async _onSubmitBackup(response) {
        const backupFileName = `${this.state.backupFilename}.${this.state.backupFormat}`;

        const blob = await response.blob();

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = backupFileName;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
    }

    async _executeAction(action) {
        const formData = this.formData;
        try {
            // The `rename` action is a `duplicate` followed by a `drop`.
            const route = `/web/database/${(action === "rename") ? "duplicate" : action}`;
            const response = await fetch(route, {
                method: "POST",
                body: formData,
            });
            if (!response.ok) {
                this.notification.add(`Action failed. Check password.`, { type: "danger" });
                this.state.isProcessing = false;
                if (action === "drop" && response.status === 500) {
                    location.reload();
                }
                return;
            }
            switch (action) {
                case "backup":
                    await this._onSubmitBackup(response);
                    break;
                case "duplicate":
                    break;
                case "drop":
                    // Reloading leads the user to the database manager.
                    location.reload();
                    break;
                case "rename":
                    this._executeAction("drop");
                    break;
            }
            this.props.close();
            this.notification.add(_t("Action completed successfully!"), { type: "success" });

        } catch (error) {
            console.error(error);
            this.notification.add(_t("A network error occurred."), { type: "danger" });
            this.state.isProcessing = false;
        }
    }

    async onSubmit() {
        this.state.isProcessing = true;
        await this._executeAction(this.props.action);
    }
}
