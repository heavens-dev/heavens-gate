from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.common import bot_cfg


admin_commands_router = Router()
admin_commands_router.message.filter(
    F.from_user.id.in_(bot_cfg.admins)
)

@admin_commands_router.message(Command("admin_help"))
async def admin_help(message: Message):
    await message.answer("Сам справишься.")

# TODO: make it work
# @dp.message(Command("reboot"))
# async def reboot(message: Message) -> None:
#     with open(".reboot", "w", encoding="utf-8") as f:
#         f.write(str(message.chat.id))

#     os.execv(sys.executable, ['python'] + sys.argv)