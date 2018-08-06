from django import forms
from django.core.validators import ValidationError
import datetime


class RenewBookForm(forms.Form):
    renewal_date = forms.DateField(help_text='Enter a date between now and 4 weeks (default 3)')

    def clean_renewal_date(self):
        data = self.cleaned_data['renewal_date']

        # Check date is not in the past
        if data < datetime.date.today():
            raise ValidationError('Invalid date - renewal cannot be in the past')

        # Check date does not exceed max renewal of +4 weeks
        if data > datetime.date.today() + datetime.timedelta(weeks=4):
            raise ValidationError('Invalid date - renewal cannot exceed 4 weeks')

        return data
