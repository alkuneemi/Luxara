import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";
import { encodeOptionsToParams } from "@html_editor/main/media/video/utils";

export class Dailymotion extends ThirdPartyVideoAbstract {
    static id = "dailymotion";
    static name = "Dailymotion";
    static urlMatcher =
        /^(https?:\/\/)(www\.)?(dailymotion\.com\/(embed\/video\/|embed\/|video\/|hub\/.*#video=)|geo\.dailymotion\.com\/player\.html\?video=|dai\.ly\/)(?<id>[A-Za-z0-9]{6,7})(?:[-_][-_a-z]*)?(?:[?&=](?:[0-9a-z]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["startTime"] },
    };
    /**
     * Returns the embed url for a dailymotion video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const params = encodeOptionsToParams(options, Dailymotion.optionsConfig);
        return `https://geo.dailymotion.com/player.html?video=${videoId}${
            params ? "&" + params : ""
        }`;
    }
    /**
     * Returns the url for the thumbnail image of the video.
     *
     * @param {string} videoId
     * @return {string} url
     */
    static getThumbnailUrl(videoId) {
        return `https://www.dailymotion.com/thumbnail/video/${videoId}`;
    }
    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://www.dailymotion.com/video/x7svr6t",
        extra: "https://www.dailymotion.com/video/x2jvvep_hakan-yukur-klip_sport",
        embed: "https://geo.dailymotion.com/player.html?video=x7svr6t",
        minified: "dai.ly/x7svr6t",
        params: "https://www.dailymotion.com/video/x7svr6t?startTime=62",
        embedParams: "https://geo.dailymotion.com/player.html?video=x7svr6t&startTime=62",
        // This is the old embed url of dailymotion,
        // we keep supporting it for backward compatibility reasons,
        // but it should not be used anymore.
        dailymotion_old_embed: "https://www.dailymotion.com/embed/video/x578has?autoplay=1",
    };
}
