"""
Обработчик команды /start и привязки номера телефона.
Адаптировано под maxapi: MessageCreated, event.message.answer()
"""
import re
from maxapi.types import MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.database.crud import get_or_create_user

async def handle_start(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Начало диалога: проверка авторизации, запрос телефона"""
    chat_id = event.message.recipient.chat_id
    user_obj = getattr(event.message, "from_user", None) or getattr(event.message, "user", None)
    name = getattr(user_obj, "first_name", "Пользователь") if user_obj else "Пользователь"

    logger.info(f"Handling /start for chat_id {chat_id}, user_obj {user_obj}, name {name}")

    # Получаем или создаём пользователя в БД
    db_user = await get_or_create_user(db, chat_id, name=name)
    logger.info(f"DB user after get_or_create: {db_user}, id: {db_user.id}, name: {db_user.name}, phone: {db_user.phone}")

    if db_user.phone:
        logger.info(f"Sending answer for user with phone")
        try:
            await event.message.answer(
                f"👋 Привет, {name}! Ваш номер уже привязан: `{db_user.phone}`\n\n"
                f"📋 Доступные команды:\n"
                f"/idea — подать инициативу\n"
                f"/list — посмотреть одобренные инициативы\n"
                f"/vote [номер] — проголосовать"
            )
            logger.info(f"Answer sent successfully")
        except Exception as e:
            logger.error(f"Error sending answer: {e}")
        return

    # Переходим в состояние ожидания телефона
    user_states[chat_id] = {"step": "waiting_phone"}
    logger.info(f"Sending phone request to chat_id {chat_id}")
    try:
        await event.message.answer(
            "📱 Для продолжения отправьте ваш номер телефона в формате:\n"
            "`+79991234567`"
        )
        logger.info(f"Answer sent successfully")
    except Exception as e:
        logger.error(f"Error sending answer: {e}")


async def handle_phone_input(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Обработка ввода номера телефона"""
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip()

    if chat_id not in user_states or user_states[chat_id].get("step") != "waiting_phone":
        return

    if not re.match(r"^\+7\d{10}$", text):
        await event.message.answer(
            "❌ Неверный формат. Пожалуйста, введите номер в формате: `+79991234567`"
        )
        return

    # Сохраняем телефон и очищаем состояние
    await get_or_create_user(db, chat_id, phone=text)
    del user_states[chat_id]

    await event.message.answer(
        f"✅ Номер `{text}` успешно привязан!\n"
        f"Теперь вы можете подать инициативу командой `/idea`"
    )
    logger.info(f"Пользователь {chat_id} привязал телефон: {text}")