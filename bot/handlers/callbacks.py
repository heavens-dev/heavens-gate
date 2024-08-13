from aiogram import F
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.types import CallbackQuery, BufferedInputFile

from bot.utils.callback_data import (ConnectionPeerCallbackData, 
                                     UserActionsCallbackData,
                                     UserActionsEnum)
from config.loader import user_router, admin_router, bot_instance
from bot.handlers.keyboards import build_user_actions_keyboard
from core.wg.wgconfig_helper import get_peer_config_str
from bot.utils.user_helper import get_user_data_string
from core.db.db_works import ClientFactory
from core.db.enums import StatusChoices


@user_router.callback_query(ConnectionPeerCallbackData.filter())
async def select_peer_callback(callback: CallbackQuery, callback_data: ConnectionPeerCallbackData):

    client = ClientFactory(tg_id=callback.from_user.id).get_client()

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

@admin_router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.BAN_USER)
)
async def ban_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    client.set_status(StatusChoices.STATUS_ACCOUNT_BLOCKED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} заблокирован.")
    await callback.message.edit_text(get_user_data_string(client))
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))

@admin_router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.PARDON_USER)
)
async def pardon_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(tg_id=callback_data.user_id).get_client()
    client.set_status(StatusChoices.STATUS_CREATED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} разблокирован.")
    await callback.message.edit_text(get_user_data_string(client))
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))
