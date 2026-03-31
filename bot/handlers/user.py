from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.handlers.keyboards import (build_peer_configs_keyboard,
                                    build_user_actions_keyboard,
                                    cancel_keyboard)
from bot.middlewares.logging_middleware import LoggingMiddleware
from bot.utils.states import ContactAdminStates, RenamePeerStates
from bot.utils.user_helper import (get_user_data_string,
                                   unblock_timeout_connections)
from core.db.db_works import ClientFactory
from core.db.enums import SubscriptionType

router = Router(name="user")
router.message.middleware.register(LoggingMiddleware())


@router.message(Command("me"))
async def me(message: Message):
    client = ClientFactory(user_id=message.chat.id).get_client()

    user_data = get_user_data_string(client)

    await message.answer(user_data[0])
    await message.answer(
        text=user_data[1],
        reply_markup=build_user_actions_keyboard(client, is_admin=False)
    )

@router.message(Command("config"))
async def get_config(message: Message):
    client = ClientFactory(user_id=message.from_user.id).get_client()
    peers = client.get_all_peers()

    if not peers:
        await message.answer("❌ У тебя нет пиров.")
        return

    keyboard = build_peer_configs_keyboard(message.from_user.id, peers)
    await message.answer(
        text="Выбери конфиг, который ты хочешь получить, из клавиатуры: ",
        reply_markup=keyboard
    )

@router.message(Command("unblock"))
async def unblock_connections(message: Message):
    client = ClientFactory(user_id=message.from_user.id).get_client()

    unblock_timeout_connections(client)

    await message.answer("✅ Соединения были разблокированы/обновлены. Можешь продолжать пользоваться VPN!")

@router.message(Command("change_peer_name"))
async def change_peer_name(message: Message, state: FSMContext):
    client = ClientFactory(user_id=message.from_user.id).get_client()
    keyboard = build_peer_configs_keyboard(client.userdata.user_id, client.get_all_peers(), display_all=False)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await message.answer(
        text="Выбери конфиг, который хочешь переименовать:",
        reply_markup=keyboard
    )
    await state.set_state(RenamePeerStates.peer_selection)

@router.message(Command("contact"))
async def contact(message: Message, state: FSMContext):
    await message.answer("✏️ Напиши сообщение, которое хочешь отправить администраторам"
                         " (или <code>отмена</code>, если передумал):", reply_markup=cancel_keyboard())
    await state.set_state(ContactAdminStates.message_entering)

@router.message(Command("whats_new"))
async def whats_new(message: Message):
    msg = """<b>Что нового?</b>

<blockquote> 🌇 <b>Новые подписки</b></blockquote>
Мы предоставляем теперь отдельный доступ к обходу белых списков в подписке Heaven's Gate ☀️ Clear. Классическая подписка также никуда не пропала, и все клиенты по умолчанию остаются именно на ней.

<blockquote> 🌐 <b>Подписки VLess</b></blockquote>
Теперь для доступа к нескольким конфигурациям XRay ты можешь использовать одну ссылку на подписку VLess. Подписки обновляют конфигурации, если они как-либо изменяются, так что тебе не нужно беспокоиться о том, что конфиг может устареть.

<blockquote> 🛜 <b>Heaven's Relay</b></blockquote>
Головной сервер Relay теперь является частью основной инфраструктуры. Это значит, что мы сможем добавлять новые локации быстрее, а ты сможешь выбирать, к какой локации подключаться без необходимости стучаться к нам за новым конфигом.
(доступно временно только для клиентов с подпиской ☀️ Clear)

У нас всё ещё есть планы по добавлению новых функций, и это не все перечисленные нововведения.
Спасибо, что остаёшься с нами. Чистого неба над головой, и свободного и быстрого интернета! 🩵
"""

    await message.answer(msg)

@router.message(Command("about_sub"))
async def about_subscription(message: Message):
    msg = "<b>Типы подписок:</b>"

    for subscription_type in SubscriptionType:
        msg += f"<blockquote>{SubscriptionType.to_string(subscription_type)}</blockquote>\n"
        msg += f"{SubscriptionType.description(subscription_type)}\n\n"

    await message.answer(msg)
