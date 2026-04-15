import { unmockedOrm } from "@web/../tests/_framework/module_set.hoot";

let webSiteId;
export const getWebsiteId = async () => {
    if (!webSiteId) {
        const webSiteIds = await unmockedOrm("website", "get_current_website", [], {});
        webSiteId = webSiteIds[0];
    }
    return webSiteId;
};
