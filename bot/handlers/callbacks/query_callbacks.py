from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import default_state
from aiogram.types import BufferedInputFile, CallbackQuery
from aiogram.utils.media_group import MediaGroupBuilder

from bot.handlers.keyboards import (build_peer_configs_keyboard,
                                    build_protocols_keyboard,
                                    build_user_actions_keyboard,
                                    cancel_keyboard, extend_time_keyboard)
from bot.utils.callback_data import (GetUserCallbackData, PeerCallbackData,
                                     PreviewMessageCallbackData,
                                     ProtocolChoiceCallbackData,
                                     TimeExtenderCallbackData,
                                     UserActionsCallbackData, UserActionsEnum,
                                     YesOrNoEnum)
from bot.utils.states import (AddPeerStates, ContactAdminStates,
                              ExtendTimeStates, PreviewMessageStates,
                              RenamePeerStates, WhisperStates)
from bot.utils.user_helper import extend_users_usage_time, get_user_data_string
from config.loader import bot_instance, server_cfg, wghub
from core.db.db_works import ClientFactory
from core.db.enums import ClientStatusChoices, PeerStatusChoices
from core.logs import bot_logger
from core.utils.date_utils import parse_time
from core.wg.wgconfig_helper import get_peer_config_str

router = Router(name="callbacks")


@router.callback_query(F.data == "cancel_action")
async def cancel_action_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("❌ Действие отменено.")

@router.callback_query(PeerCallbackData.filter(), default_state)
async def select_peer_callback(callback: CallbackQuery, callback_data: PeerCallbackData, state: FSMContext):
    client = ClientFactory(user_id=callback_data.user_id).get_client()

    peers = client.get_wireguard_peers(is_amnezia=wghub.is_amnezia)
    media_group = MediaGroupBuilder()
    additional_interface_data = None
    await state.clear()

    if wghub.is_amnezia:
        additional_interface_data = {
            "Jc": peers[0].Jc,
            "Jmin": peers[0].Jmin,
            "Jmax": peers[0].Jmax,
            "Junk": server_cfg.junk
        }

    for peer in peers:
        if callback_data.peer_id == -1:
            media_group.add_document(
                media=BufferedInputFile(
                    file=bytes(get_peer_config_str(server_cfg, peer, additional_interface_data), encoding="utf-8"),
                    filename=f"{peer.peer_name or peer.id}_wg.conf"
                )
            )
        elif peer.id == callback_data.peer_id:
            media_group.add_document(
                BufferedInputFile(
                    file=bytes(get_peer_config_str(server_cfg, peer, additional_interface_data), encoding="utf-8"),
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
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    peers = client.get_wireguard_peers()
    client.set_status(ClientStatusChoices.STATUS_ACCOUNT_BLOCKED)
    # if peer has no peers, it will raise KeyError, so we suppress it
    wghub.disable_peers(peers)
    for peer in peers:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_BLOCKED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} заблокирован.")
    # see docstring in get_user_data_string for more info
    await callback.message.edit_text(get_user_data_string(client)[1])
    await callback.message.edit_reply_markup(reply_markup=build_user_actions_keyboard(client))

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.PARDON_USER)
)
async def pardon_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    peers = client.get_wireguard_peers()
    client.set_status(ClientStatusChoices.STATUS_CREATED)
    wghub.enable_peers(peers)
    for peer in peers:
        client.set_peer_status(peer.id, PeerStatusChoices.STATUS_DISCONNECTED)
    await callback.answer(f"✅ Пользователь {client.userdata.name} разблокирован.")
    await callback.message.edit_text(
        # see docstring in get_user_data_string for more info
        text=get_user_data_string(client)[1],
        reply_markup=build_user_actions_keyboard(client)
    )

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.GET_CONFIGS)
)
async def get_user_configs_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    peers = ClientFactory(user_id=callback_data.user_id).get_client().get_all_peers()

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

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.UPDATE_DATA)
)
async def update_user_message_data(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    await callback.answer(f"Данные пользователя {client.userdata.name} обновлены.")
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(
            # see docstring in get_user_data_string for more info
            text=get_user_data_string(client)[1],
            reply_markup=build_user_actions_keyboard(client, is_admin=callback_data.is_admin)
        )

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.ADD_PEER)
)
async def add_peer_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData, state: FSMContext):
    client = ClientFactory(user_id=callback_data.user_id).get_client()

    keyboard = build_protocols_keyboard()
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])

    await callback.message.answer("ℹ️ Выбери протокол", reply_markup=keyboard)

    await state.set_state(AddPeerStates.select_protocol)
    await state.set_data({
        "user_id": client.userdata.user_id,
    })

    await callback.answer()

    # try:
    #     ip_addr = ip_queue.get_ip()
    # except Exception:
    #     await callback.message.answer("❌ Нет доступных IP-адресов!")
    #     bot_logger.error("❌ Tried to add a peer, but no IP addresses are available.")
    #     return
    # new_peer = client.add_wireguard_peer(shared_ips=ip_addr, peer_name=f"{client.userdata.name}_{last_id}", is_amnezia=wghub.is_amnezia)
    # wghub.add_peer(new_peer)
    # with bot_logger.contextualize(peer=new_peer):
    #     bot_logger.info(f"New peer was created manually by {callback.message.from_user.username}")
    # await callback.answer("✅ Пир добавлен.")

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

    msg = "📨 <b>Сообщение от администрации</b>:\n\n" \
          if len(message_data["user_ids"]) <= 1 \
          else "✉️ <b>Рассылка от администрации</b>:\n\n"

    for tg_id in message_data["user_ids"]:
        await callback.bot.send_message(tg_id, msg + message_data["message"])

    await callback.message.answer("✅ Сообщение отправлено!")

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.CHANGE_PEER_NAME)
)
async def change_peer_name_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData, state: FSMContext):
    client = ClientFactory(user_id=callback.from_user.id).get_client()
    keyboard = build_peer_configs_keyboard(client.userdata.user_id, client.get_all_peers(), display_all=False)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await callback.answer()
    await callback.message.answer(
        text="Выбери конфиг, который хочешь переименовать:",
        reply_markup=keyboard
    )
    await state.set_state(RenamePeerStates.peer_selection)

@router.callback_query(PeerCallbackData.filter(), RenamePeerStates.peer_selection)
async def change_peer_name_entering_callback(callback: CallbackQuery, callback_data: PeerCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("🔤 Введи новое имя для конфига (или <code>отмена</code>, если передумал):",
                                  reply_markup=cancel_keyboard())
    await state.set_state(RenamePeerStates.name_entering)
    await state.set_data({"tg_id": callback_data.user_id, "peer_id": callback_data.peer_id})

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.EXTEND_USAGE_TIME)
)
async def extend_usage_time_dialog_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData):
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    keyboard = extend_time_keyboard(client.userdata.user_id)
    keyboard.inline_keyboard.append(cancel_keyboard().inline_keyboard[0])
    await callback.answer()
    await callback.message.answer("🕒 На сколько продлить время использования?", reply_markup=keyboard)

@router.callback_query(
    TimeExtenderCallbackData.filter(F.extend_for != "custom")
)
async def extend_usage_time_callback(callback: CallbackQuery, callback_data: TimeExtenderCallbackData):
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    time_to_add = parse_time(callback_data.extend_for)

    if not time_to_add:
        bot_logger.warning(f"Invalid time format, couldn't parse: {callback_data.extend_for}")
        await callback.answer(f"❌ Неправильный формат времени: {callback_data.extend_for}")
        return

    if extend_users_usage_time(client, time_to_add):
        await callback.answer(f"✅ Время использования продлено на {callback_data.extend_for}.")
    else:
        await callback.answer(f"❓ Что-то пошло не так во время операции. Проверь логи.")

@router.callback_query(
    TimeExtenderCallbackData.filter(F.extend_for == "custom")
)
async def extend_usage_time_custom(callback: CallbackQuery, callback_data: TimeExtenderCallbackData, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer(f"📅 Введи время, на которое ты хочешь продлить доступ в формате "
                                  "<code>число</code> + <code>(d -- дни, w -- недели, M -- месяцы, Y -- годы)</code>: ",
                                  reply_markup=cancel_keyboard())
    await state.set_data({"user_id": callback_data.user_id, "extend_for": callback_data.extend_for})
    await state.set_state(ExtendTimeStates.time_entering)

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.CONTACT_ADMIN)
)
async def contact_admin_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("✏️ Напиши сообщение, которое хочешь отправить администраторам"
                                  " (или <code>отмена</code>, если передумал):", reply_markup=cancel_keyboard())
    await state.set_state(ContactAdminStates.message_entering)

@router.callback_query(
    UserActionsCallbackData.filter(F.action == UserActionsEnum.WHISPER_USER)
)
async def whisper_user_callback(callback: CallbackQuery, callback_data: UserActionsCallbackData, state: FSMContext):
    await callback.answer()
    await state.set_data({"user_id": callback_data.user_id})
    await state.set_state(WhisperStates.message_entering)
    await callback.message.answer("✏️ Введи сообщение:", reply_markup=cancel_keyboard())

@router.callback_query(GetUserCallbackData.filter())
async def get_user_callback(callback: CallbackQuery, callback_data: GetUserCallbackData):
    client = ClientFactory(user_id=callback_data.user_id).get_client()
    await callback.answer()
    user_data = get_user_data_string(client)
    await callback.message.answer(f"Пользователь: {client.userdata.name}\n" + user_data[0])
    await callback.message.answer(
        user_data[1],
        reply_markup=build_user_actions_keyboard(client, is_admin=True)
    )

@router.callback_query(ProtocolChoiceCallbackData.filter())
async def protocol_choice_callback(
    callback: CallbackQuery,
    callback_data: ProtocolChoiceCallbackData,
    state: FSMContext):

    data = await state.get_data()

    if data.get("user_id", None) is None:
        await callback.answer("❌ Ты начал процедуру добавления пира не с команды /add_peer или кнопки.")
        await state.clear()
        return

    await callback.message.answer(
        "Введи количество пиров, которое ты хочешь добавить (или <code>отмена</code>, если передумал):",
        reply_markup=cancel_keyboard()
    )

    await state.set_state(AddPeerStates.select_amount)
    await state.update_data(protocol=callback_data.protocol)

    await callback.answer()
