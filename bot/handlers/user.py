from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config.loader import bot_cfg
from core.db.db_works import Users


user_router = Router()
