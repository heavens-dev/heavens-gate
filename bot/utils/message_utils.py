from aiogram.fsm.context import FSMContext

from bot.handlers.keyboards import preview_keyboard
from bot.utils.states import PreviewMessageStates
from config.loader import bot_cfg, bot_instance


async def preview_message(msg: str, chat_id: int, state: FSMContext, clients_list: list[int]):
    await state.set_state(PreviewMessageStates.preview)
    await state.set_data(data=dict(message=msg, user_ids=clients_list))

    await bot_instance.send_message(chat_id=chat_id, text=
        "✉️ <b>Проверь правильность твоего сообщения перед отправкой</b>.\n"
        + "\n--------------------------------------------\n"
        + msg
        + "\n--------------------------------------------"
        + "\n<b>Отправить?</b>",
        reply_markup=preview_keyboard()
    )

async def send_error_message(chat_id: int, action: str):
    await bot_instance.send_message(chat_id=chat_id, text="❌ Произошла ошибка во время выполнения команды. Пожалуйста, напиши об этом инцеденте нам.")
    for admin in bot_cfg.admins:
        await bot_instance.send_message(chat_id=admin, text=f"❗️ Произошла ошибка во время выполнения команды. Пользователь {chat_id} столкнулся с проблемой. Действие: {action}. Проверь логи.")
