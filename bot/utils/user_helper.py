from typing import Optional, Union

from pydantic import ValidationError

from core.db.db_works import Client, ClientFactory
from core.db.enums import ClientStatusChoices
from core.utils.check import check_ip_address


def get_client_by_id_or_ip(id_or_ip: Union[str, int]) -> tuple[Optional[Client], Optional[str]]:
    """Tries to get client by it's id or ip.
    Returns `(Client, None)` if the user was found, `(None, "error_message")` otherwise"""
    if check_ip_address(id_or_ip):
        client = ClientFactory.get_client(id_or_ip)
    else:
        try:
            client = ClientFactory(tg_id=id_or_ip).get_client()
        except ValidationError:
            client = None

    if client is None:
        return None, f"❌ Пользователь <code>{id_or_ip}</code> не найден."
    return client, None

def get_user_data_string(client: Client) -> str:
    """Returns human-readable data about User.
    Recommended to use `parse_mode="HTML"`."""
    return f"""ℹ️ Информация об аккаунте:
ID: {client.userdata.telegram_id}
Текущий статус: {ClientStatusChoices.to_string(client.userdata.status)}
IP: {client.userdata.ip_address}

📅 Дата регистрации: {client.userdata.registered_at.strftime("%d %b %Y в %H:%M")}
"""
