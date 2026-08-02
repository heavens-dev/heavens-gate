import datetime
from typing import Optional

import humanize

from config.loader import xray_worker
from core.db.db_works import OrganizationRepository
from core.logs import bot_logger


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
        expire_time = f'Подписка истекает <b>{org_repo.orgdata.subscription_expiry.strftime("%d.%m.%Y")}</b>\n'
        if org_repo.orgdata.subscription_expiry > datetime.datetime.now():
            expire_time += f'Осталось времени: <b>{humanize.naturaldelta(org_repo.orgdata.subscription_expiry - datetime.datetime.now(), months=False)}</b>'
        else:
            expire_time += "❌ Подписка истекла"
    else:
        expire_time = "❌ Не оплачено"

    return f"""🏢 <b>Организация:</b> <code>{org_repo.orgdata.name}</code> (ID: <code>{org_repo.orgdata.org_id}</code>)

🕓 <b>Информация о подписке</b>:
<blockquote>{expire_time}</blockquote>

👥 <b>Количество участников</b>: <b>{len(members)}</b>
👑 <b>Владельцы</b>: {', '.join([f'<code>{owner.name} ({owner.user_id})</code>' for owner in owners])}
"""


def extend_organization_subscription_time(org: OrganizationRepository, time_to_add: datetime.timedelta) -> bool:
    """Extends the organization subscription expiry and synchronizes it to all members.

    Args:
        org (OrganizationRepository): Organization repository object
        time_to_add (datetime.timedelta): Time to add to the current expiry

    Returns:
        bool: True if the operation was successful, False otherwise.
    """
    now = datetime.datetime.now()

    if not isinstance(org.orgdata.subscription_expiry, datetime.datetime) or org.orgdata.subscription_expiry < now:
        org.orgdata.subscription_expiry = now

    new_expiry = org.orgdata.subscription_expiry + time_to_add

    if not org.set_organization_expiry(new_expiry):
        bot_logger.error(f"Couldn't update expire time for organization {org.orgdata.org_id}!")
        return False

    org.sync_subscription_to_members()

    if xray_worker.remnawave:
        for member in org.get_members():
            xray_worker.remnawave_update_user(
                member,
                expire_at=new_expiry
            )

    return True
