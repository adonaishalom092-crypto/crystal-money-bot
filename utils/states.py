from aiogram.dispatcher.filters.state import State, StatesGroup

class WithdrawState(StatesGroup):
    method = State()
    number = State()
    name = State()
    confirm = State()

class BroadcastState(StatesGroup):
    message = State()

class AddChannelState(StatesGroup):
    username = State()

class BanState(StatesGroup):
    user_id = State()

class UnbanState(StatesGroup):
    user_id = State()
