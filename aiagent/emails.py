from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

SUBJECT = {
    "morning": "【基金看板】午间新闻速览 + 仓位建议",
    "evening": "【基金看板】一日新闻速览 + 明日仓位建议",
    "ondemand": "【基金看板】AI 报告（按需）",
}


def send_report_email(report) -> int:
    if not report.user.email:
        return 0
    host = getattr(settings, "SITE_HOST", "http://49.234.26.95:8188")
    html = render_to_string("aiagent/emails/%s.html" % report.type,
                            {"report": report, "host": host})
    subject = SUBJECT.get(report.type, "【基金看板】AI 报告")
    msg = EmailMultiAlternatives(subject, "请用支持 HTML 的客户端查看", to=[report.user.email])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
    return 1
