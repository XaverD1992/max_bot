"""
Точка входа бота TOS MVP.
Поддерживает polling и webhook режимы через переменную окружения RUN_MODE.
"""
import asyncio
import logging
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated, MessageCallback

from src.config import settings
from src.logging_config import logger
from src.database.session import engine, async_session_factory
from src.models import Base
from src.handlers import start, idea, moderation, list, vote, admin, callback

# Хранилище состояний диалогов (для MVP — in-memory)
user_states: dict[int, dict] = {}

async def init_db():
    """Создание таблиц при первом запуске"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ База данных инициализирована")

def register_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков событий"""

    @dp.bot_started()
    async def bot_started(event: BotStarted):
        await event.bot.send_message(
            chat_id=event.chat_id,
            text='Привет! Отправь мне /start'
    )
    
    # === Команда /start ===
    @dp.message_created(Command('start'))
    async def on_start(event: MessageCreated):
        async with async_session_factory() as db:
            await start.handle_start(event, db, user_states)
    
    # === Обработка ввода телефона (после /start) ===
    @dp.message_created()
    async def on_phone_input(event: MessageCreated):
        chat_id = event.message.recipient.chat_id
        if chat_id in user_states and user_states[chat_id].get("step") == "waiting_phone":
            async with async_session_factory() as db:
                await start.handle_phone_input(event, db, user_states)
    
    # === Подача инициативы: /idea ===
    @dp.message_created(Command('idea'))
    async def on_idea_start(event: MessageCreated):
        async with async_session_factory() as db:
            await idea.handle_idea_start(event, db, user_states)
    
    # === Шаги диалога подачи инициативы ===
    @dp.message_created()
    async def on_idea_step(event: MessageCreated):
        chat_id = event.message.recipient.chat_id
        if chat_id in user_states:
            step = user_states[chat_id].get("step")
            if step in ["waiting_title", "waiting_description", "waiting_location"]:
                async with async_session_factory() as db:
                    await idea.handle_idea_step(event, db, user_states)
            elif step == "waiting_reject_reason":
                async with async_session_factory() as db:
                    await moderation.handle_reject_reason(event, db, user_states)
    
    # === Список инициатив: /list ===
    @dp.message_created(Command('list'))
    async def on_list(event: MessageCreated):
        async with async_session_factory() as db:
            await list.handle_list(event, db)
    
    # === Голосование: /vote ===
    @dp.message_created(Command('vote'))
    async def on_vote(event: MessageCreated):
        async with async_session_factory() as db:
            await vote.handle_vote(event, db)
    
    # === Админ-команда: /set_role ===
    @dp.message_created(Command('set_role'))
    async def on_set_role(event: MessageCreated):
        async with async_session_factory() as db:
            await admin.handle_set_role(event, db)
    
    # === Обработка callback (кнопки) ===
    @dp.message_callback()
    async def on_callback(callback: MessageCallback):
        async with async_session_factory() as db:
            await callback.handle_callback(callback, db, user_states)

async def main():
    """Точка входа"""
    await init_db()
    
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher()
    
    register_handlers(dp)
    
    logger.info(f"🤖 Бот запущен | Режим: {settings.RUN_MODE} | DB: {settings.DB_URL}")
    
    if settings.RUN_MODE == "webhook":
        if not settings.WEBHOOK_URL:
            logger.error("❌ WEBHOOK_URL не указан для webhook-режима!")
            return
        # Для webhook требуется: pip install maxapi[webhook]
        await dp.handle_webhook(
            bot=bot,
            host="0.0.0.0",
            port=8080,
            log_level=settings.LOG_LEVEL.lower()
        )
    else:
        # Polling-режим для локальной разработки
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())