from django.template.loader import render_to_string

CAT_LABELS = {"politics": "时政国际", "finance": "A股财经",
              "finance_oversea": "海外财经", "tech": "科技"}


def render(analysis: dict, report_type: str) -> str:
    return render_to_string("aiagent/_report_body.html",
                            {"analysis": analysis, "report_type": report_type,
                             "cat_labels": CAT_LABELS})
