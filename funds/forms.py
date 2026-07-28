from django import forms
from django.forms import formset_factory
from .models import Fund, Tag

WEEKDAY_CHOICES = [(i, w) for i, w in enumerate(
    ["周一", "周二", "周三", "周四", "周五", "周六", "周日"])]


class FundForm(forms.ModelForm):
    """基金添加/编辑表单——面向普通用户：中文标签、必填星标、选填标注、字段释义。"""

    class Meta:
        model = Fund
        fields = ["name", "code", "market", "confirm_delay", "invest_amount",
                  "invest_frequency", "invest_weekday", "start_date", "start_total",
                  "fund_type", "risk_level", "currency", "tags", "is_active", "end_date", "is_cleared"]
        labels = {
            "name": "基金名称",
            "code": "基金代码",
            "market": "市场",
            "confirm_delay": "份额确认时间",
            "invest_amount": "每次定投金额",
            "invest_frequency": "定投频率",
            "invest_weekday": "定投日",
            "start_date": "起购日",
            "start_total": "起购前已有持仓",
            "fund_type": "基金类型",
            "risk_level": "风险等级",
            "currency": "币种",
            "tags": "标签",
            "is_active": "仍在定投",
            "end_date": "停投日",
            "is_cleared": "已清仓",
        }
        help_texts = {
            "name": "你给这只基金起的名字，方便自己识别。",
            "code": "如 000001、005827。支付宝基金详情页可查。",
            "market": "决定交易日历：A股按沪深交易日，美股按美股交易日。",
            "confirm_delay": "买入后第几天确认份额。A股基金一般 T+1，美股/QDII 一般 T+2。",
            "invest_amount": "每个定投日扣款的金额（元）。",
            "invest_frequency": "每日 = 每个交易日扣款；每周 = 固定某一天扣款。",
            "invest_weekday": "只在「每周」时需要填。",
            "start_date": "你第一次买入、且份额已确认的那天。系统从这天开始记账。",
            "start_total": "起购日【之前】已经持有的市值（含当时待确认）。从第一笔买入当天开始记就填 0 或留空。",
            "fund_type": "用于后续按类型分组统计。",
            "risk_level": "R1 最低 ~ R5 最高。",
            "currency": "默认人民币。",
            "tags": "如：科技、消费、新能源。可自由添加，方便分类。",
            "is_active": "勾选=仍在定投。取消后每日投入自动变 0，但仍持仓、仍要记每日盈亏。",
            "end_date": "停投的日期。取消「仍在定投」时填，留空默认记为今天。",
            "is_cleared": "勾选=已全部卖出、不再追踪每日盈亏（清仓，与「停投」不同）。",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "如：易方达蓝筹精选"}),
            "code": forms.TextInput(attrs={"placeholder": "005827"}),
            "market": forms.Select(),
            "confirm_delay": forms.Select(choices=[(1, "T+1（A股基金）"), (2, "T+2（美股/QDII）")]),
            "invest_amount": forms.NumberInput(attrs={"step": "0.01", "placeholder": "5"}),
            "invest_frequency": forms.Select(),
            "invest_weekday": forms.Select(choices=WEEKDAY_CHOICES),
            "start_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "start_total": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0"}),
            "fund_type": forms.Select(),
            "risk_level": forms.Select(),
            "currency": forms.Select(),
            "tags": forms.SelectMultiple(attrs={"size": "6"}),
            "is_active": forms.CheckboxInput(),
            "end_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "is_cleared": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 选填字段
        for name in ["code", "start_total", "invest_weekday", "fund_type", "risk_level",
                     "currency", "tags", "end_date"]:
            self.fields[name].required = False
        # 统一套 Bootstrap 样式
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault("class", "form-check-input")
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault("class", "form-select")
            else:
                w.attrs.setdefault("class", "form-control")


class DailyEntryForm(forms.Form):
    fund = forms.IntegerField(widget=forms.HiddenInput)
    profit = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "如 0.84"}))
    profit_ratio = forms.DecimalField(
        max_digits=7, decimal_places=4, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.0001", "placeholder": "选填"}))
    invested = forms.DecimalField(
        max_digits=12, decimal_places=2, required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}))


DailyEntryFormSet = formset_factory(DailyEntryForm, extra=0)
