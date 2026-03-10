import {
    Component,
    onWillStart,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { Cache } from "@web/core/utils/cache";

const svgCache = new Cache(async (src) => {
    let text;
    try {
        const response = await window.fetch(src);
        text = await response.text();
    } catch {
        // In some tours, the tour finishes before the fetch is done
        // and when a tour is finished, the python side will ask the
        // browser to stop loading resources. This causes the fetch
        // to fail and throw an error which crashes the test even
        // though it completed successfully.
        // So return an empty SVG to ensure everything completes
        // correctly.
        text = "<svg></svg>";
    }
    const parser = new window.DOMParser();
    const xmlDoc = parser.parseFromString(text, "text/xml");
    return xmlDoc.getElementsByTagName("svg")[0];
}, JSON.stringify);

// Tracks which images have been loaded in this session.
// Used to skip lazy loading on re-mount (e.g., panel re-open).
const loadedImages = new Set();

/**
 * Image component with optional lazy loading support.
 *
 * @prop {String} src - Image source URL
 * @prop {String} [class] - CSS class(es) to apply
 * @prop {String} [style] - Inline styles
 * @prop {String} [alt] - Alt text for accessibility
 * @prop {Object} [attrs] - Additional HTML attributes
 * @prop {Boolean} [svgCheck=true] - Parse .svg files as XML for full SVG
 *  support
 * @prop {Boolean} [lazyLoad=false] - Defer loading until image enters
 * viewport.
 *
 * When true, renders a placeholder and uses IntersectionObserver to
 * trigger loading. Useful for long lists (e.g., shape thumbnails).
 */
export class Image extends Component {
    static props = {
        src: String,
        class: { type: String, optional: true },
        style: { type: String, optional: true },
        alt: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        svgCheck: { type: Boolean, optional: true },
        lazyLoad: { type: Boolean, optional: true },
    };
    static defaultProps = {
        svgCheck: true,
        lazyLoad: false,
    };
    static template = xml`
        <t t-if="state.loaded">
            <svg t-if="isSvg(props.src)" t-ref="svg"
                xmlns="http://www.w3.org/2000/svg"
                t-att-width="svg.width"
                t-att-viewBox="svg.viewBox"
                t-att-fill="svg.fill"
                class="hb-svg d-flex m-auto"
                t-att-class="props.class"
                t-att-style="props.style"
                t-att="props.attrs"/>
            <img t-else=""
                t-att-src="props.src"
                t-att-class="props.class"
                t-att-style="props.style"
                t-att-alt="props.alt"
                t-att="props.attrs"/>
        </t>
        <span t-elif="env.imgGroup &amp; !props.lazyLoad" t-ref="placeholder"
            style="display:inline-block;width:100%;aspect-ratio:1;visibility:hidden;"/>
        <span t-elif="props.lazyLoad" t-ref="placeholder"
            style="display:inline-block;width:100%;aspect-ratio:1;"/>
        `;

    setup() {
        this.svgRef = useRef("svg");
        this.placeholderRef = useRef("placeholder");
        this.svg = {};
        this.state = useState({ loaded: false });

        onWillStart(async () => {
            // If already loaded before, load immediately (from browser cache).
            // This prevents placeholders from flashing on panel re-open.
            if (loadedImages.has(this.props.src) || !this.props.lazyLoad) {
                await this.handleImgLoad(this.props.src);
            }
        });

        onWillUpdateProps(async (nextProps) => {
            if (this.props.src !== nextProps.src) {
                this.state.loaded = false;
                await this.handleImgLoad(nextProps.src);
            }
        });
        // Set up IntersectionObserver for lazy loading after the
        // placeholder <span> is mounted in the DOM.
        // useEffect's cleanup function handles disconnect on both:
        //   - component destroy.
        //   - state.loaded → true placeholder span removed.
        useEffect(
            (placeholderEl) => {
                if (!placeholderEl) {
                    return;
                }
                if ("IntersectionObserver" in window) {
                    // Start loading slightly before the thumbnail scrolls
                    // fully into view to reduce perceived latency.
                    const PRELOAD_MARGIN = "500px";
                    const observer = new IntersectionObserver(
                        (entries) => {
                            for (const entry of entries) {
                                if (entry.isIntersecting) {
                                    this.handleImgLoad(this.props.src);
                                    observer.disconnect();
                                }
                            }
                        },
                        { rootMargin: PRELOAD_MARGIN }
                    );
                    observer.observe(placeholderEl);
                    return () => observer.disconnect();
                } else {
                    // Fallback: load immediately if no IntersectionObserver.
                    this.handleImgLoad(this.props.src);
                }
            },
            () => [this.placeholderRef.el]
        );

        useEffect(
            (imgLoaded) => {
                if (imgLoaded && this.isSvg(this.props.src) && this.svg.children.length) {
                    // We can't use t-out with markup because it is parsed as HTML,
                    // but SVG need to be parsed as XML for all features to work.
                    const children = [];
                    for (const child of this.svg.children) {
                        children.push(child.cloneNode(true));
                    }
                    this.svgRef.el.replaceChildren(...children);
                }
            },
            () => [this.state.loaded]
        );
    }

    async handleImgLoad(src) {
        const prom = this.isSvg(src) ? this.getSvg() : this.loadImage(src);
        if (this.isSvg(src)) {
            prom.then((svg) => {
                this.svg = svg;
            });
        }
        if (this.env.imgGroup && !this.props.lazyLoad) {
            this.env.imgGroup.addImgProm(prom, () => {
                this.state.loaded = true;
            });
        } else {
            await prom;
            loadedImages.add(src);
            this.state.loaded = true;
        }
    }

    loadImage() {
        return new Promise((resolve) => {
            const img = new window.Image();
            img.onload = () => resolve({ status: "loaded" });
            img.onerror = () => resolve({ status: "error" });
            img.src = this.props.src;
        });
    }

    isSvg(src) {
        return this.props.svgCheck && src.split(".").pop() === "svg";
    }

    async getSvg() {
        const svgEl = (await svgCache.read(this.props.src)).cloneNode(true);
        return {
            viewBox: svgEl.getAttribute("viewBox"),
            width: svgEl.getAttribute("width") || "",
            fill: svgEl.getAttribute("fill") || "",
            children: svgEl.children,
        };
    }
}
