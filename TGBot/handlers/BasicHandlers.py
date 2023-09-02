from aiogram import Bot
from aiogram.types import Message


class Handlers:
    @staticmethod
    async def get_start(message: Message, bot: Bot):
        await bot.send_message(message.from_user.id, f'Hi {message.from_user.username}. Nice to meet you!!!')