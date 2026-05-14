"""
Точка входа бота TOS MVP.
Поддерживает polling и webhook режимы через переменную окружения RUN_MODE.
"""
import asyncio
import logging
from maxapi import Bot, Dispatcher, F
from maxapi.types import BotStarted, Command, MessageCreated, MessageCallback
from maxapi.context import MemoryContext

from src.config import settings
from src.logging_config import logger
from src.database.session import engine, async_session_factory
from src.models import Base
from src.handlers import start, idea, moderation, list, vote, admin, callback
from src.bot.states import IdeaStates, StartStates, ModerationStates

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
    async def on_start(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            await start.handle_start(event, db, context)
    
    # === Подача инициативы: /idea ===
    @dp.message_created(Command('idea'))
    async def on_idea_start(event: MessageCreated, context: MemoryContext):
        logger.info(f"[main] on_idea_start: получена команда /idea от chat_id={event.message.recipient.chat_id}")
        async with async_session_factory() as db:
            await idea.handle_idea_start(event, db, context)
    
    # === Шаги диалога подачи инициативы ===
    @dp.message_created(F.message.body.text, IdeaStates.WAITING_TITLE)
    async def on_title(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            try:
                await idea.handle_idea_step(event, db, context)
            except Exception as e:
                logger.exception(f"[main] Ошибка в handle_idea_step для chat_id={event.message.recipient.chat_id}: {e}")

    @dp.message_created(F.message.body.text, IdeaStates.WAITING_DESCRIPTION)
    async def on_description(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            try:
                await idea.handle_idea_step(event, db, context)
            except Exception as e:
                logger.exception(f"[main] Ошибка в handle_idea_step: {e}")

    @dp.message_created(F.message.body.text, IdeaStates.WAITING_LOCATION)
    async def on_location(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            try:
                await idea.handle_idea_step(event, db, context)
            except Exception as e:
                logger.exception(f"[main] Ошибка в handle_idea_step: {e}")

    @dp.message_created(F.message.body.text, IdeaStates.CONFIRM_SUBMIT)
    async def on_confirm(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            try:
                await idea.handle_idea_step(event, db, context)
            except Exception as e:
                logger.exception(f"[main] Ошибка в handle_idea_step: {e}")

    @dp.message_created(F.message.body.text, ModerationStates.WAITING_REJECT_REASON)
    async def on_reject_reason(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            try:
                await moderation.handle_reject_reason(event, db, context)
            except Exception as e:
                logger.exception(f"[main] Ошибка в handle_reject_reason: {e}")

    # === Обработка ввода телефона (после /start) ===
    @dp.message_created(F.message.body.text.regexp(r"^\+7\d{10}$"), StartStates.WAITING_PHONE)
    async def on_phone_input(event: MessageCreated, context: MemoryContext):
        async with async_session_factory() as db:
            await start.handle_phone_input(event, db, context)

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
    async def on_callback(callback: MessageCallback, context: MemoryContext):
        async with async_session_factory() as db:
            await callback.handle_callback(callback, db, context)

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
        await dp.handle_webhook(
            bot=bot,
            host="0.0.0.0",
            port=8080,
            log_level=settings.LOG_LEVEL.lower()
        )
    else:
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())