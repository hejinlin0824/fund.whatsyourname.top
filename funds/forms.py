from django import forms
from django.forms import formset_factory
from .models import Fund, Tag


class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ["name", "code", "market", "confirm_delay", "invest_amount",
                  "invest_frequency", "invest_weekday", "start_date", "start_total",
                  "fund_type", "risk_level", "currency", "is_active", "tags"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}


class DailyEntryForm(forms.Form):
    fund = forms.IntegerField(widget=forms.HiddenInput)
    profit = forms.DecimalField(max_digits=12, decimal_places=2, required=False)
    profit_ratio = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    invested = forms.DecimalField(max_digits=12, decimal_places=2, required=False)


DailyEntryFormSet = formset_factory(DailyEntryForm, extra=0)
