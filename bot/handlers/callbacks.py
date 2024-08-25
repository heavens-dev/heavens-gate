from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import CallbackQuery, BufferedInputFile

from bot.utils.callback_data import (PreviewMessageCallbackData,
                                     ConnectionPeerCallbackData,
                                     UserActionsCallbackData,
                                     UserActionsEnum,
                                     YesOrNoEnum)
from config.loader import bot_instance
from bot.handlers.keyboards import (build_user_actions_keyboard,
                                    build_peer_configs_keyboard)
from core.wg.wgconfig_helper import get_peer_config_str
from bot.utils.user_helper import get_user_data_string
from bot.utils.states import PreviewMessageStates
from core.db.db_works import ClientFactory
from core.db.enums import StatusChoices


router = Router(name="callbacks")


@router.callback_query(ConnectionPeerCallbackData.filter())
async def select_peer_callback(callback: CallbackQuery, callback_data: ConnectionPeerCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    peers = client.get_peers()
    media_group = MediaGroupBuilder()

    for peer in peers:
        if callback_data.peer_id == -1:
            media_group.add_document(
                media=BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
        elif peer.id == callback_data.peer_id:
            media_group.add_document(
                BufferedInputFile(
                    file=bytes(get_peer_config_str(peer), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
            break

    await bot_instance.send_media_group(callback.from_user.id, media=media_group.build())
    await callback.message.delete()
    await callback.answer()

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.BAN_USER)
)
async def ban_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    client.set_status(StatusChoices.STATUS_ACCOUNT_BLOCKED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} заблокирован.")
    await callback.message.edit_text(get_user_data_string(client))
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.PARDON_USER)
)
async def pardon_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    client.set_status(StatusChoices.STATUS_CREATED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} разблокирован.")
    await callback.message.edit_text(get_user_data_string(client))
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.GET_CONFIGS)
)
async def get_user_configs_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    peers = ClientFactory(tg_id=callback_data.user_id).get_client().get_peers()

    await callback.answer()
    if peers:
        builder = build_peer_configs_keyboard(callback_data.user_id, peers)
        await callback.message.answer(
            text="Выбери конфиг, который ты хочешь получить из клавиатуры: ",
            reply_markup=builder
        )
    else:
        await callback.message.answer(
            text="❌ У этого пользователя нет доступных пиров."
        )

@router.callback_query(PreviewMessageCallbackData.filter(), PreviewMessageStates.preview)
async def preview_message_callback(callback: CallbackQuery, callback_data: PreviewMessageCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    if callback_data.answer == YesOrNoEnum.ANSWER_NO:
        await callback.message.answer("❌ Отправка отменена")
        return

    # ? message_data = {message="<message_to_broadcast>", user_ids=[<telegram_ids>, ...]}
    message_data = await state.get_data()
    await state.clear()

    msg = "🤫 <b>Сообщение от администрации</b>:\n\n" \
          if len(message_data["user_ids"]) <= 1 \
          else "✉️ <b>Рассылка от администрации</b>:\n\n"

    for tg_id in message_data["user_ids"]:
        await callback.bot.send_message(tg_id, msg + message_data["message"])

    await callback.message.answer("✅ Сообщение отправлено!")
