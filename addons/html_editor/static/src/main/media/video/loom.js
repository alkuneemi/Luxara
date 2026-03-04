import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";
import { encodeOptionsToParams, BooleanInt } from "@html_editor/main/media/video/utils";

export class Loom extends ThirdPartyVideoAbstract {
    static id = "loom";
    static name = "Loom";

    static urlMatcher =
        /^https:\/\/(?:www\.)?loom\.com\/(?:embed|share)\/(?<id>[0-9a-z]+)\\?(?:[?&]([0-9a-zA-Z]+)=([0-9a-zA-Z_-]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["t"] },
        autoplay: { default: false, type: BooleanInt, params: ["autoplay"] },
        muted: { default: false, type: BooleanInt, params: ["muted"] },
    };
    /**
     * Returns the embed url for a loom video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Loom.optionsConfig);
        return `https://www.loom.com/embed/${videoId}${params ? "?" + params : ""}`;
    }
    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://www.loom.com/share/e5b8c04bca094dd8a5507925ab887002",
        embed: "https://www.loom.com/embed/e5b8c04bca094dd8a5507925ab887002",
        Params: "loom.com/share/e5b8c04bca094dd8a5507925ab887002?autoplay=1&t=62",
        embedParams: "https://www.loom.com/embed/e5b8c04bca094dd8a5507925ab887002?autoplay=1&t=62s",
    };
}
