import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export class Instagram extends ThirdPartyVideoAbstract {
    static id = "instagram";
    static name = "Intagram";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:(.*)instagram\.com|instagr\.am)\/(?:p|reel)\/(?<id>[a-zA-Z0-9\-_\\.]+)(?:\/embed)?\/?$/i;

    /**
     * Returns the embed url for a Instagram video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        return `https://www.instagram.com/p/${videoId}/embed/`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {string} url
     */
    static getThumbnailUrl(videoId) {
        return `https://www.instagram.com/p/${videoId}/media/?size=t`;
    }
    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://www.instagram.com/p/B6dXGTxggTG",
        minified: "instagr.am/p/B6dXGTxggTG/",
        reel: "https://www.instagram.com/reel/B6dXGTxggTG/",
        embed: "https://www.instagram.com/p/B6dXGTxggTG/embed/",
    };
}
