import { browser } from "@web/core/browser/browser";
import { Chatter } from "@mail/chatter/web_portal_project/chatter";
import { patch } from "@web/core/utils/patch";

const chatterPatch = {
    setup() {
        super.setup(...arguments);
        this.state.showReviewComposer = false;
    },

    async _reloadReviews(thread) {
        const fetched = await thread.fetchMessages();
        const limit = this.store.FETCH_LIMIT;
        thread.loadOlder = fetched.length > limit;
        thread.messages = fetched.slice(-limit);
        thread.rating_stats = fetched.at(-1)?.rating_stats || thread.rating_stats;
    },

    async onReviewPostCallback() {
        this.state.showReviewComposer = false;
        const { thread } = this.state;
        Object.assign(thread, { loadOlder: false, selectedRating: false, messages: [] });
        await this._reloadReviews(thread);
    },

    async onClickStarDomain(star) {
        const { thread } = this.state;
        Object.assign(thread, { loadOlder: false, selectedRating: star });
        await this._reloadReviews(thread);
    },

    async onClickStarDomainReset() {
        const { thread } = this.state;
        Object.assign(thread, { loadOlder: false, selectedRating: false });
        await this._reloadReviews(thread);
    },

    get ratingStats() {
        return this.state.thread?.messages.at(-1)?.rating_stats || this.state.thread?.rating_stats;
    },

    get loginRedirectUrl() {
        return `/web/login?redirect=${encodeURIComponent(browser.location.pathname + "#discussion")}`;
    },
};

patch(Chatter.prototype, chatterPatch);
