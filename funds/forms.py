from django import forms
from .models import Fund, Tag


class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ["name", "code", "market", "confirm_delay", "invest_amount",
                  "invest_frequency", "invest_weekday", "start_date", "start_total",
                  "fund_type", "risk_level", "currency", "is_active", "tags"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}
