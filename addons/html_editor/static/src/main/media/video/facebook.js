import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export class Facebook extends ThirdPartyVideoAbstract {
    static id = "facebook";
    static name = "Facebook";
    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.)?facebook\.com(?:\/(?:[^/]+\/)?videos\/|\/watch\/?\?v=|(?:\/username)?\/reel\/|\/plugins\/video\.php\?[^ ]*?href=.*?(?:videos|reel)%2f)(?<id>\d+)(\/|%2f)?$/i;

    /**
     * Returns the embed url for a facebook video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const encodedUrl = encodeURIComponent(
            `https://www.facebook.com/username/videos/${videoId}/`
        );
        return `https://facebook.com/plugins/video.php?href=${encodedUrl}`;
    }

    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://www.facebook.com/username/videos/2206239373151307/",
        watch: "facebook.com/watch/?v=2206239373151307",
        reel: "https://www.facebook.com/username/reel/2206239373151307/",
        embed: "https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fusername%2Fvideos%2F2206239373151307%2F",
    };
}
