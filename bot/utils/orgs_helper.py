import datetime

import humanize

from core.db.db_works import OrganizationRepository


def build_organization_info(org_repo: OrganizationRepository) -> str:
    """Returns human-readable data about an Organization. Recommended to use `parse_mode="HTML"`.

    Args:
        org_repo (OrganizationRepository): Organization repository object

    Returns:
        str: Human-readable data about Organization
    """
    members = org_repo.get_members()
    owners = org_repo.get_owners()

    if org_repo.orgdata.subscription_expiry:
        expire_time = f'Подписка истекает: <b>{org_repo.orgdata.subscription_expiry.strftime("%d.%m.%Y")}</b>\n'
        if org_repo.orgdata.subscription_expiry > datetime.datetime.now():
            expire_time += f'Осталось времени: <b>{humanize.naturaldelta(org_repo.orgdata.subscription_expiry - datetime.datetime.now(), months=False)}</b>'
        else:
            expire_time += "❌ Подписка истекла"
    else:
        expire_time = "❌ Не оплачено"

    return f"""🏢 <b>Организация:</b> <code>{org_repo.orgdata.name}</code> (ID: <code>{org_repo.orgdata.org_id}</code>)
<blockquote>Подписка истекает {expire_time}
👥 Количество участников: <b>{len(members)}</b>
Владельцы: <b>{', '.join([f'<code>{owner.orgdata.name} ({owner.orgdata.id})</code>' for owner in owners])}</b></blockquote>
"""
