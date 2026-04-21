from odoo import http
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


class TestWebsiteEventSale(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):

    def test_website_event_sale_free_tickets(self):
        """ Test saleorder is not created for tickets free tickets """
        self.authenticate(None, None)
        free_ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'Free',
            'product_id': self.product_event.id,
            'price': 0,
        })
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        existing_so = self.env['sale.order'].search([])
        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertEqual(self.env['sale.order'].search([]), existing_so, "Sale order should not be created for the free tickets")
        self.assertEqual(len(self.event.registration_ids), event_registration_count + 1)

    def test_website_event_sale_free_paid_mix(self):
        """ Test saleorder is created if paid ticket selected """
        self.authenticate(None, None)
        free_ticket = self.env['event.event.ticket'].create({
            'event_id': self.event.id,
            'name': 'Free',
            'product_id': self.product_event.id,
            'price': 0,
        })
        event_questions = self.event.question_ids
        event_registration_count = len(self.event.registration_ids)
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'Bob',
            f'1-email-{email_question.id}': 'bob@test.lan',
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': self.ticket.id,
            f'2-name-{name_question.id}': 'joe',
            f'2-email-{email_question.id}': 'joe@test.lan',
            f'2-phone-{phone_question.id}': '8989898988',
            '2-event_ticket_id': free_ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })

        self.assertEqual(len(self.event.registration_ids), event_registration_count + 2)
        self.assertTrue(self.env['sale.order'].search([
            ('order_line.event_ticket_id', '=', self.ticket.id),
            ('order_line.event_ticket_id', '=', free_ticket.id)
        ]), "Sale order should be created for the free/paid tickets mix")

    def test_website_event_sale_mandatory_signup_single_partner(self):
        """ Event registration must not pre-create a partner when signup is mandatory. """
        self.env['website'].get_current_website().account_on_checkout = 'mandatory'
        self.authenticate(None, None)
        attendee_email = 'new.attendee@test.lan'
        existing_partners_with_email = self.env['res.partner'].search([('email', '=', attendee_email)])
        event_questions = self.event.question_ids
        name_question = event_questions.filtered(lambda q: q.question_type == 'name')
        email_question = event_questions.filtered(lambda q: q.question_type == 'email')
        phone_question = event_questions.filtered(lambda q: q.question_type == 'phone')
        response = self.url_open(f'/event/{self.event.id}/registration/confirm', data={
            f'1-name-{name_question.id}': 'New Attendee',
            f'1-email-{email_question.id}': attendee_email,
            f'1-phone-{phone_question.id}': '8989898989',
            '1-event_ticket_id': self.ticket.id,
            'csrf_token': http.Request.csrf_token(self),
        })
        self.assertTrue(
            response.url.endswith('/web/login?redirect=/shop/checkout'),
            f"Public user must be sent to the login/signup step before checkout, got {response.url}",
        )

        partners_with_email = self.env['res.partner'].search([('email', '=', attendee_email)])
        self.assertEqual(
            partners_with_email, existing_partners_with_email,
            "No partner should be pre-created for the attendee when signup is mandatory; "
            "the signup step is responsible for creating it.",
        )
        order = self.env['sale.order'].search(
            [('order_line.event_ticket_id', '=', self.ticket.id)], order='id desc', limit=1,
        )
        self.assertTrue(order, "The paid event registration must create a sale order.")
        public_partner = self.env.ref('base.public_user').partner_id
        self.assertEqual(
            order.partner_id, public_partner,
            "The cart must remain anonymous so that signup can assign its own partner to it.",
        )
