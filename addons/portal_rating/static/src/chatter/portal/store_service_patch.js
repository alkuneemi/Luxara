import { Message } from "@mail/core/common/message_model";
import { Store } from "@mail/core/common/store_service";
import { Thread as ThreadComponent } from "@mail/core/common/thread";
import { Thread as ThreadModel } from "@mail/core/common/thread_model";
import { PortalChatterService } from "@portal/chatter/portal/portal_chatter_service";

import { patch } from "@web/core/utils/patch";

patch(Store.prototype, {
    setup() {
        super.setup(...arguments);
        this.isReviewChatter = false;
    },

    async getMessagePostParams({ postData }) {
        const params = await super.getMessagePostParams(...arguments);
        if (postData.rating_value) {
            params.post_data.rating_value = postData.rating_value;
        }
        return params;
    },
});

patch(PortalChatterService.prototype, {
    setup() {
        super.setup(...arguments);
        const chatterEl = document.querySelector(".o_portal_chatter");
        if (
            chatterEl?.getAttribute("data-display_rating") === "True" &&
            parseInt(chatterEl.getAttribute("data-allow_composer"))
        ) {
            this.store.FETCH_LIMIT = 3;
            this.store.isReviewChatter = true;
        }
    },
});

patch(Message.prototype, {
    get bubbleColor() {
        return this.store.isReviewChatter ? undefined : super.bubbleColor;
    },

    get authorName() {
        if (this.store.isReviewChatter && this.author_id?.pseudonymize_name) {
            return this.author_id.pseudonymize_name;
        }
        return super.authorName;
    },

    async remove() {
        const isRating = this.rating_value || this.rating_id;
        if (!this.store.isReviewChatter || !this.thread || !isRating) {
            return super.remove(...arguments);
        }
        const data = await super.remove(...arguments);
        this.thread.loadOlder = false;
        const fetched = await this.thread.fetchMessages();
        const limit = this.thread.store.FETCH_LIMIT;
        this.thread.loadOlder = fetched.length > limit;
        this.thread.messages = fetched.slice(-limit);
        return data;
    },
});

patch(ThreadComponent.prototype, {
    onClickLoadOlder() {
        this.props.thread._reviewManualLoad = true;
        try {
            return super.onClickLoadOlder(...arguments);
        } finally {
            this.props.thread._reviewManualLoad = false;
        }
    },
});

patch(ThreadModel.prototype, {
    async fetchMoreMessages() {
        if (this.store.isReviewChatter && !this._reviewManualLoad) {
            return;
        }
        return super.fetchMoreMessages(...arguments);
    },

    async fetchNewMessages(options = {}) {
        if (!this.store.isReviewChatter) {
            return super.fetchNewMessages(...arguments);
        }
        return this._withBumpedFetchLimit(async (origLimit) => {
            await super.fetchNewMessages(options);
            if (this.messages.length > origLimit) {
                this.messages = this.messages.slice(-origLimit);
            }
        });
    },

    async fetchMessages(options = {}) {
        if (!this.store.isReviewChatter || this._reviewFetchBumped) {
            return super.fetchMessages(...arguments);
        }
        return this._withBumpedFetchLimit(() => super.fetchMessages(options));
    },

    async _withBumpedFetchLimit(fn) {
        const origLimit = this.store.FETCH_LIMIT;
        this._reviewFetchBumped = true;
        this.store.FETCH_LIMIT = origLimit + 1;
        try {
            return await fn(origLimit);
        } finally {
            this._reviewFetchBumped = false;
            this.store.FETCH_LIMIT = origLimit;
        }
    },
});
