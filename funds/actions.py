"""记录用户对基金的关键操作，供当日 AI 总结参考。"""
from datetime import date as _date


def log_action(user, kind, text, d=None):
    from aiagent.models import ActionLog
    ActionLog.objects.create(user=user, date=d or _date.today(), kind=kind, text=text)


def log_fund_create(user, fund):
    log_action(user, "fund_added",
               f"新增基金 {fund.name}（{fund.get_market_display()}/{fund.get_fund_type_display()}，每期定投 {fund.invest_amount}）")


def log_fund_edit(user, fund, old):
    """old: 保存前的关键字段快照 dict（invest_amount/is_active/is_cleared/name）。"""
    name = fund.name
    changed = False
    if old.get("is_cleared") != fund.is_cleared and fund.is_cleared:
        log_action(user, "cleared", f"{name} 清仓")
        changed = True
    if old.get("is_active") and not fund.is_active:
        log_action(user, "stopped", f"{name} 停投（仍持仓）")
        changed = True
    elif not old.get("is_active") and fund.is_active:
        log_action(user, "resumed", f"{name} 恢复定投")
        changed = True
    if old.get("invest_amount") != fund.invest_amount:
        log_action(user, "invest_changed",
                   f"{name} 定投金额 {old.get('invest_amount')} → {fund.invest_amount}")
        changed = True
    if old.get("name") and old.get("name") != fund.name:
        log_action(user, "edited", f"基金改名 {old.get('name')} → {name}")
        changed = True
    if not changed:
        log_action(user, "edited", f"{name} 资料更新")
