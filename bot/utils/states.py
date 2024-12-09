from aiogram.fsm.state import State, StatesGroup


class PreviewMessageStates(StatesGroup):
    preview = State()

class RenamePeerStates(StatesGroup):
    peer_selection = State()
    name_entering = State()

class ContactAdminStates(StatesGroup):
    message_entering = State()

class WhisperStates(StatesGroup):
    message_entering = State()
