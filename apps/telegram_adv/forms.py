from django import forms
from django.core.exceptions import ValidationError
from django.contrib.admin import widgets, site as admin_site

from .models import ReceiverChannel, CampaignFile, BankAccount, TelegramChannel


class BankAccountExchangeForm(forms.Form):
    from_bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.all(),
        widget=widgets.ForeignKeyRawIdWidget(TelegramChannel._meta.get_field('sheba').remote_field, admin_site),
    )
    to_bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.all(),
        widget=widgets.ForeignKeyRawIdWidget(TelegramChannel._meta.get_field('sheba').remote_field, admin_site),
    )

    def clean(self):
        cleaned_data = super().clean()
        fba = cleaned_data.get('from_bank_account')
        tba = cleaned_data.get('to_bank_account')
        if fba == tba:
            raise ValidationError("these two fields shouldn't be same")
