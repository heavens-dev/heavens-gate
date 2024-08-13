from aiogram.filters.callback_data import CallbackData


class ConnectionPeerCallbackData(CallbackData, prefix="peer"):
    """Peer callback data for keyboards.

    Args:
        peer_id (int, True): integer if we want to get single peer. True if we want to get ALL peers that related to some user
    """
    peer_id: int
