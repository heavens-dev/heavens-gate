from typing import Optional
from aiogram.types import Message

from core.db.db_works import ClientFactory, Client
from core.utils.check import check_ip_address
from core.db.enums import StatusChoices
from pydantic import ValidationError


async def get_client_by_id_or_ip(message: Message) -> Optional[Client]:
    """Not a command"""
    args = message.text.split()
    if len(args) <= 1:
        await message.answer("❌ Сообщение должно содержать IP адрес пользователя или его Telegram ID.")
        return None
    
    if check_ip_address(args[1]):
        client = ClientFactory.get_client(args[1])
    else:
        try:
            client = ClientFactory(tg_id=args[1]).get_client()
        except ValidationError:
            client = None

    if client is None:
        await message.answer(f"❌ Пользователь <code>{args[1]}</code> не найден.", parse_mode="HTML")
        return None
    return client

def get_user_data_string(client: Client) -> str:
    return f"""ℹ️ Информация об аккаунте:
ID: {client.userdata.telegram_id}
Текущий статус: {StatusChoices.to_string(client.userdata.status)}
IP: {client.userdata.ip_address}

📅 Дата регистрации: {client.userdata.registered_at.strftime("%d %b %Y в %H:%M")}
"""
