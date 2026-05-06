import { Image } from "@html_builder/core/img";
import { ImgGroup } from "@html_builder/core/img_group";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { expect, test, describe } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

defineMailModels();

test("ImgGroup batches images - all appear together after all load", async () => {
    const defs = {
        img1: Promise.withResolvers(),
        img2: Promise.withResolvers(),
        img3: Promise.withResolvers(),
    };
    patchWithCleanup(Image.prototype, {
        loadImage() {
            const { promise: def } = defs[this.props.class];
            return Promise.all([super.loadImage(), def]);
        },
    });
    class Container extends Component {
        static components = { ImgGroup, Image };
        static template = xml`
            <ImgGroup>
                <t t-foreach="Object.keys(defs)" t-as="key" t-key="key">
                    <Image src="''" t-att-class="key"/>
                </t>
            </ImgGroup>`;
        static props = {};
        setup() {
            this.defs = defs;
        }
    }
    await mountWithCleanup(Container);

    // No images until all resolve
    for (const key in defs) {
        expect("img").toHaveCount(0);
        defs[key].resolve();
        await animationFrame();
    }
    // All appear together
    expect("img").toHaveCount(3);
});

test("Image lazyLoad defers loading until visible", async () => {
    let observeCallback;
    patchWithCleanup(window, {
        IntersectionObserver: class {
            constructor(callback) {
                observeCallback = callback;
            }
            observe() {}
            disconnect() {}
        },
    });

    const def = Promise.withResolvers();
    let loadCalled = false;
    patchWithCleanup(Image.prototype, {
        loadImage() {
            loadCalled = true;
            return def.promise;
        },
    });

    class Container extends Component {
        static components = { Image };
        static template = xml`<Image src="'/test.png'" lazyLoad="true"/>`;
        static props = {};
    }
    await mountWithCleanup(Container);

    // Shows placeholder, not image
    expect("img").toHaveCount(0);
    expect("span").toHaveCount(1);
    expect(loadCalled).toBe(false);

    // Simulate visibility
    observeCallback([{ isIntersecting: true }]);
    await animationFrame();
    expect(loadCalled).toBe(true);

    // Resolve load
    def.resolve({ status: "loaded" });
    await animationFrame();
    expect("img").toHaveCount(1);
    expect("span").toHaveCount(0);
});

test("Lazy-loaded images inside ImgGroup appear individually as they load", async () => {
    const observeCallbacks = [];
    patchWithCleanup(window, {
        IntersectionObserver: class {
            constructor(callback) {
                observeCallbacks.push(callback);
            }
            observe() {}
            disconnect() {}
        },
    });

    const defs = {
        img1: Promise.withResolvers(),
        img2: Promise.withResolvers(),
        img3: Promise.withResolvers(),
    };
    patchWithCleanup(Image.prototype, {
        loadImage() {
            const { promise: def } = defs[this.props.class];
            return Promise.all([super.loadImage(), def]);
        },
    });

    class Container extends Component {
        static components = { ImgGroup, Image };
        static template = xml`
            <ImgGroup>
                <t t-foreach="Object.keys(defs)" t-as="key" t-key="key">
                    <Image src="''" t-att-class="key" lazyLoad="true"/>
                </t>
            </ImgGroup>`;
        static props = {};
        setup() {
            this.defs = defs;
        }
    }
    await mountWithCleanup(Container);

    // All placeholders
    expect("img").toHaveCount(0);
    expect("span").toHaveCount(3);

    // All become visible
    for (const cb of observeCallbacks) {
        cb([{ isIntersecting: true }]);
    }
    await animationFrame();

    // Still no images - waiting for load promises
    expect("img").toHaveCount(0);

    // Lazy-loaded images bypass ImgGroup batching and appear individually
    defs.img1.resolve();
    await animationFrame();
    expect("img").toHaveCount(1);

    defs.img2.resolve();
    await animationFrame();
    expect("img").toHaveCount(2);

    defs.img3.resolve();
    await animationFrame();
    expect("img").toHaveCount(3);
});
