import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { models } from "@web/../tests/web_test_helpers";

export class MailComposeMessage extends models.ServerModel {
    _name = "mail.compose.message";

    web_save(ids, values, kwargs = {}) {
        const context = kwargs.context || {};
        if (!context.is_editing_message || !context.default_message_id) {
            return super.web_save(ids, values, kwargs);
        }
        const messageId = context.default_message_id;
        const MailMessage = this.env["mail.message"];
        const [message] = MailMessage.browse(messageId);
        if (!message) {
            return [];
        }
        const msg_values = {};
        if (values.body !== null) {
            msg_values.body = values.body || "";
        }
        MailMessage.write([messageId], msg_values);
        this.env["bus.bus"]._sendone(
            MailMessage._bus_notification_target(message.id),
            "mail.record/insert",
            new mailDataHelpers.Store(MailMessage.browse(message.id)).get_result()
        );
        return [
            {
                id: messageId,
                body: values.body || "",
            },
        ];
    }
}
