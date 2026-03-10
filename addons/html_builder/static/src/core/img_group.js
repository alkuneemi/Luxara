import { Component, useSubEnv, xml } from "@odoo/owl";
import { batched } from "@web/core/utils/timing";

/**
 * Groups child Image components to display them together once all are loaded.
 * Prevents "popcorn" effect where images appear one by one as they load.
 *
 * Usage:
 *   <ImgGroup>
 *       <Image src="..."/>
 *       <Image src="..."/>
 *   </ImgGroup>
 *
 * How it works:
 * - Each Image registers its load promise via `addImgProm(promise, onLoaded)`
 * - Images are initially hidden (visibility: hidden) to prevent
 *   staggering
 * - batched() collects all registrations in a single microtask
 * - Once all promises resolve, all onLoaded callbacks fire together
 * - All images become visible simultaneously when state.loaded = true
 */
export class ImgGroup extends Component {
    static template = xml`<t><t t-slot="default"/></t>`;
    static props = {
        slots: Object,
    };

    setup() {
        this.imgItems = [];
        this.loadImgs = batched(this._loadImgs.bind(this));

        useSubEnv({
            imgGroup: {
                addImgProm: (promise, onLoaded) => {
                    this.imgItems.push({ promise, onLoaded });
                    this.loadImgs();
                },
            },
        });
    }

    async _loadImgs() {
        const items = this.imgItems;
        this.imgItems = [];
        await Promise.all(items.map((item) => item.promise));
        for (const item of items) {
            item.onLoaded();
        }
    }
}
