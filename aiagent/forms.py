from django import forms


class DeepSeekKeyForm(forms.Form):
    deepseek_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "sk-..."}),
        required=False, label="DeepSeek API Key")
