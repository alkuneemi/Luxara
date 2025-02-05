import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
import { LinkTrackerDialog } from "../components/dialog/link_tracker_dialog";
import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { session } from "@web/session";

registry.category("website_custom_menus").add("website_links.menu_link_tracker", {
    Component: LinkTrackerDialog,
    isDisplayed: (env) => env.services.website.currentWebsite && env.services.website.contentWindow,
    getProps: async ({ orm, website, notification }) => {
        const model = "link.tracker";
        return {
            resModel: model,
            onRecordSave: async function (record) {
                const changes = await record.getChanges();
                const records = await orm.call(
                    "link.tracker",
                    "search_or_create_and_read",
                    [[changes]],
                    {}
                );
                // 'document.hasFocus()' is used to check if the browser tab is focused.
                // This check is necessary because, during the tour, it fails and gives
                // the error: "Failed to execute 'writeText' on 'Clipboard': Document is not focused."
                if (records.length && document.hasFocus()) {
                    this.currentResId = records[0].id;
                    const trackUrl = records[0].short_url;
                    await browser.navigator.clipboard.writeText(trackUrl);
                    const message = markup`
                        <div class="d-flex justify-content-between">
                            ${_t("Tracked link copied to clipboard.")}
                            <a class="btn btn-link" href="/odoo/action-website_links.action_link_tracker_tree">
                                ${_t("Manage")}
                            </a>
                        </div>
                        <div>
                            <span style=" display: -webkit-box; -webkit-line-clamp: 1;
                                -webkit-box-orient: vertical; overflow: hidden;">
                                ${_t("Link: ")}
                                ${trackUrl.replace(session["web.base.url"], "")}
                            </span>
                        </div>
                    `;
                    notification.add(message, {
                        type: "success",
                    });
                }
                return records;
            },
        };
    },
});
