from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.handlers.keyboards import build_reply_to_message_keyboard
from bot.utils.message_utils import preview_message
from bot.utils.states import (AddPeerStates, ContactAdminStates,
                              ExtendTimeStates, RenamePeerStates,
                              WhisperStates)
from bot.utils.user_helper import extend_users_subscription_time
from config.loader import (bot_cfg, bot_instance, ip_queue, wghub, xray_cfg,
                           xray_worker)
from core.db.db_works import ClientFactory
from core.db.enums import ProtocolType
from core.logs import bot_logger
from core.utils.date_utils import parse_time

router = Router(name="state_callbacks")


@router.message(RenamePeerStates.name_entering)
async def finally_change_peer_name(message: Message, state: FSMContext):
    new_name = message.text

    if new_name.lower() in ["отмена", "cancel"]:
        await state.clear()
        await message.answer("❌ Действие отменено.")
        return

    if len(new_name) >= 16:
        await message.answer("❌ Название конфига должно содержать меньше 16 символов!")
        await state.clear()
        return

    data = await state.get_data()
    user_id, peer_id = data.values()
    client = ClientFactory(user_id=user_id).get_client()
    client.change_peer_name(peer_id, new_name)
    xray_worker.update_peer(
        ClientFactory.get_xray_peer(peer_id),
        # ! we need to pass this until xray_worker is fixed
        expiry_time=client.userdata.subscription_expiry
    )
    await state.clear()
    await message.answer("✅ Конфиг был успешно переименован!")

@router.message(ContactAdminStates.message_entering)
async def contact_admin(message: Message, state: FSMContext):
    await state.clear()
    if message.text.lower() in ["отмена", "cancel"]:
        await message.answer("❌ Действие отменено.")
        return

    for admin_id in bot_cfg.admins:
        await bot_instance.send_message(
            chat_id=admin_id,
            text=f"📩 Сообщение от пользователя {message.from_user.username} ({message.from_user.id}):\n\n{message.text}"
            f"\n\n🔗 Ответить на сообщение: <code>/whisper {message.from_user.id}</code> или по кнопке ниже.",
            reply_markup=build_reply_to_message_keyboard()
        )
    await message.answer("✅ Сообщение отправлено администраторам. Ожидай обратной связи.")

@router.message(ExtendTimeStates.time_entering)
async def extend_usage_time_custom_entered(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id, _ = data.values()

    await state.clear()

    time_to_add = parse_time(message.text)

    if not time_to_add:
        await message.answer(f"❌ Неправильный формат времени: {message.text}")
        return

    client = ClientFactory(user_id=user_id).get_client()

    if extend_users_subscription_time(client, time_to_add):
        await message.answer(f"✅ Время использования продлено на {message.text}.")
    else:
        await message.answer(f"❓ Что-то пошло не так во время операции. Проверь логи.")

@router.message(WhisperStates.message_entering)
async def whisper_state(message: Message, state: FSMContext):
    user_id = (await state.get_data())["user_id"]
    if message.text.lower() in ["отмена", "cancel"]:
        await message.answer("❌ Действие отменено.")
        await state.clear()
        return

    await preview_message(message.text, message.from_user.id, state, [user_id])

@router.message(AddPeerStates.select_amount)
async def add_peers(message: Message, state: FSMContext):
    await message.delete()
    data = await state.get_data()
    client = ClientFactory(user_id=data["user_id"]).get_client()

    try:
        for _ in range(int(message.text)):
            match data["protocol"]:
                case ProtocolType.WIREGUARD | ProtocolType.AMNEZIA_WIREGUARD:
                    ip_addr = ip_queue.get_ip()
                    peer = client.add_wireguard_peer(
                        ip_addr,
                        is_amnezia=data["protocol"] == ProtocolType.AMNEZIA_WIREGUARD
                    )
                    wghub.add_peer(peer)
                case ProtocolType.XRAY:
                    peer = client.add_xray_peer(
                        # hardcoded flow, but it's okay
                        flow="xtls-rprx-vision",
                        inbound_id=xray_cfg.inbound_id,
                    )
                    xray_worker.add_peers(
                        peer.inbound_id,
                        [peer],
                        client.userdata.subscription_expiry,
                        client.userdata.vless_sub_token
                    )
                case _:
                    raise TypeError("Unknown protocol type")
        await message.answer("✅ Пиры были успешно добавлены.")
    except ValueError:
        await message.answer("❌ Неправильный формат количества пиров. Введи число.")
    except IndexError:
        await message.answer("❌ Недостаточно свободных IP-адресов.")
        bot_logger.error("Tried to add a peer, but no IP addresses are available.")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при добавлении пиров: {e}")
        bot_logger.exception(f"Error while adding peers: {e}")
    finally:
        await state.clear()
        return
