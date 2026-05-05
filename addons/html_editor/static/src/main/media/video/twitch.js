import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";
import { encodeOptionsToParams } from "@html_editor/main/media/video/utils";

export class Twitch extends ThirdPartyVideoAbstract {
    static id = "twitch";
    static name = "Twitch";

    static urlMatcher =
        /^(?:https?:\/\/)?(?:www\.|player\.|clips\.)?twitch\.tv\/(?:(?:(?:videos\/|embed\?clip=)|\?(?:([0-9a-z]+)=([0-9a-z_\-.]+)&)*video=)|[0-9a-z_]{4,25}\/clip\/)(?<id>[0-9a-zA-Z_-]+)(?:[?&=]([0-9a-z_\-.]+))*$/i;

    static optionsConfig = {
        startFrom: { default: 0, type: Number, params: ["time"] },
        autoplay: { default: true, type: Boolean, params: ["autoplay"] },
        muted: { default: false, type: Boolean, params: ["muted"] },
        isClip: { default: false, type: Boolean },
    };

    /**
     * Returns the embed url for a Twitch video or clip.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        const isClip = options.isClip;
        const params = encodeOptionsToParams(options, Twitch.optionsConfig);
        const parentDomain = window.location.hostname;
        let embedUrl = "";
        if (isClip) {
            embedUrl = `https://clips.twitch.tv/embed?clip=`;
        } else {
            embedUrl = `https://player.twitch.tv/?video=`;
        }
        embedUrl += `${videoId}&parent=${parentDomain}${params ? "&" + params : ""}`;
        return embedUrl;
    }

    /**
     * @override
     * @param {URL} url
     */
    static getCustomUrlOptions(url) {
        return { isClip: url.hostname.includes("clip") };
    }

    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://www.twitch.tv/videos/1064007405",
        clip: "https://www.twitch.tv/monstercat/clip/UnrulyShySalamanderPogChamp?filter=clips&range=7d&sort=time",
        embed: "https://player.twitch.tv/?video=1064007405&parent=example.com",
        embedClip:
            "https://clips.twitch.tv/embed?clip=UnrulyShySalamanderPogChamp&parent=example.com",
        params: "twitch.tv/videos/1064007405?time=62&autoplay=true&muted=true",
        embedParams:
            "https://player.twitch.tv/?video=1064007405&parent=example.com&time=62&autoplay=true&muted=true",
    };
}
