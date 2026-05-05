import { ThirdPartyVideoAbstract } from "@html_editor/main/media/video/third_party_video_abstract";

export class GDriveVideo extends ThirdPartyVideoAbstract {
    static id = "gDrive";
    static name = "Google Drive";

    static urlMatcher =
        /^https:\/\/drive\.google\.com\/file\/d\/(?<id>.*?)\/.*?(?:\?[0-9a-z_\-=&]+)?$/i;

    /**
     * Returns the embed url for a Google Drive video.
     *
     * @param {string} videoId
     * @param {Object} options
     * @return {string} url
     */
    static getEmbedUrl(videoId, options = {}) {
        return `https://drive.google.com/file/d/${videoId}/preview`;
    }

    /**
     * Used to dynamicaly unit test this video provider with various urls,
     * all the urls in this object should be parsable wy the urlMatcher.
     *
     * @see /addons/html_editor/static/tests/media/*.test.js
     * */
    static unitTestUrls = {
        base: "https://drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/view?usp=sharing",
        embed: "drive.google.com/file/d/1A2B3C4D5E6F7G8H9I0J/preview",
    };
}
