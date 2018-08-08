import datetime

from django.test import SimpleTestCase
from django.utils import timezone

from catalog.forms import RenewBookForm


class RenewBookFormTest(SimpleTestCase):

    def test_renew_form_date_field_label(self):
        form = RenewBookForm()
        renewal_date_label = form.fields['renewal_date'].label
        self.assertTrue(renewal_date_label is None or renewal_date_label == 'renewal date')

    def test_renew_form_date_field_help_text(self):
        form = RenewBookForm()
        expected_help_text = 'Enter a date between now and 4 weeks (default 3)'
        self.assertEqual(form.fields['renewal_date'].help_text, expected_help_text)

    def test_renew_form_date_in_past(self):
        date = datetime.date.today() - datetime.timedelta(days=1)
        form = RenewBookForm({'renewal_date': date})
        self.assertFalse(form.is_valid())

    def test_renew_form_date_too_far_in_future(self):
        date = datetime.date.today() + datetime.timedelta(weeks=4, days=1)
        form = RenewBookForm({'renewal_date': date})
        self.assertFalse(form.is_valid())

    def test_renew_form_date_today(self):
        date = datetime.date.today()
        form = RenewBookForm({'renewal_date': date})
        self.assertTrue(form.is_valid())

    def test_renew_form_date_max(self):
        date = timezone.now() + datetime.timedelta(weeks=4)
        form = RenewBookForm({'renewal_date': date})
        self.assertTrue(form.is_valid())
