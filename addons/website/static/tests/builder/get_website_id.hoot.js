import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";

let webSiteId;
export const getWebsiteId = async () => {
    if (!webSiteId) {
        webSiteId = await unmockedOrm("website", "get_current_website", [], {});
    }
    return webSiteId;
};
