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

- Поддержка XRay. Поскольку (Amnezia) Wireguard часто не работает на мобильных провайдерах, мы рекомендуем использовать XRay в случае, когда Wireguard не работает. Учитывай, что этот протокол медленнее, чем Wireguard.
- Улучшенный интерфейс. Чтобы не путаться в куче конфигов, теперь все подключения будут специально проименованы, чтобы ты мог легко их различать.
- Рефакторинг кода. Мы переписали часть кода, чтобы он стал более читабельным и понятным. Теперь мы можем добавлять новые функции быстрее и проще.
- Обработка ошибок. Теперь бот будет обрабатывать ошибки в командах и выдавать более понятные сообщения, а также информировать админов мгновенно, если что-то пойдёт не так. Ну или будет стараться так делать.
"""

    await message.answer(msg)
