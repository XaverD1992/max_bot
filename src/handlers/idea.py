"""
Пошаговый диалог подачи инициативы.
Работает в паре с callback.py (выбор категории и подтверждение).
"""
from maxapi.types import MessageCreated
from maxapi.enums.parse_mode import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.bot.states import IdeaStates
from src.bot.keyboards import make_category_keyboard, make_confirm_keyboard

logger.info(f"[idea] IdeaStates type: {type(IdeaStates)}, WAITING_TITLE: {IdeaStates.WAITING_TITLE}, type: {type(IdeaStates.WAITING_TITLE)}")

async def handle_idea_start(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Запуск диалога подачи инициативы"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[idea] handle_idea_start вызван для chat_id={chat_id}")

    # Инициализируем состояние
    user_states[chat_id] = {"step": IdeaStates.WAITING_TITLE.value}
    try:
        await event.message.answer(
            "✍️ Введите **название** инициативы (кратко, 1-2 строки):"
            # parse_mode убран для теста
        )
        logger.info(f"[idea] Отправлено сообщение с запросом названия для chat_id={chat_id}")
    except Exception as e:
        logger.error(f"[idea] Ошибка при отправке сообщения для chat_id={chat_id}: {e}")


async def handle_idea_step(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Обработка текстовых шагов диалога"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[idea] handle_idea_step вызван для chat_id={chat_id}")

    if chat_id not in user_states:
        logger.warning(f"[idea] chat_id={chat_id} отсутствует в user_states. Текущие состояния: {list(user_states.keys())}")
        return

    step = user_states[chat_id].get("step")
    logger.info(f"[idea] Текущий шаг для chat_id={chat_id}: {step}")
    text = event.message.body.text.strip() if event.message.body.text else ""
    logger.info(f"[idea] Получен текст: '{text[:50]}...'" if len(text) > 50 else f"[idea] Получен текст: '{text}'")

    if chat_id not in user_states:
        return

    step = user_states[chat_id].get("step")

    if step == IdeaStates.WAITING_TITLE.value:
        if len(text) < 3:
            await event.message.answer("❌ Название слишком короткое. Попробуйте снова.")
            return
        user_states[chat_id]["title"] = text
        user_states[chat_id]["step"] = IdeaStates.WAITING_DESCRIPTION.value
        await event.message.answer(
            "📝 Теперь введите **описание** проблемы или предложения (подробно):",
            parse_mode=ParseMode.MARKDOWN
        )

    elif step == IdeaStates.WAITING_DESCRIPTION.value:
        if len(text) < 10:
            await event.message.answer("❌ Описание слишком короткое. Добавьте деталей.")
            return
        user_states[chat_id]["description"] = text
        user_states[chat_id]["step"] = IdeaStates.WAITING_CATEGORY.value
        
        # Отправляем клавиатуру с категориями
        kb = make_category_keyboard()
        await event.message.answer(
            "🏷️ Выберите **категорию**:",
            keyboard=kb.pack(),
            parse_mode=ParseMode.MARKDOWN
        )

    elif step == IdeaStates.WAITING_LOCATION.value:
        if len(text) < 5:
            await event.message.answer("❌ Укажите адрес подробнее (улица, дом, ориентир).")
            return
        user_states[chat_id]["location"] = text
        user_states[chat_id]["step"] = IdeaStates.CONFIRM_SUBMIT.value

        # Формируем превью для подтверждения
        data = user_states[chat_id]
        preview = (
            f"🔍 Проверьте данные перед отправкой:\n\n"
            f"📌 *{data['title']}*\n"
            f"📝 {data['description'][:150]}{'...' if len(data['description']) > 150 else ''}\n"
            f"🏷️ Категория: {data['category']}\n"
            f"📍 Адрес: {data['location']}\n\n"
            f"Отправить?"
        )
        kb = make_confirm_keyboard()
        await event.message.answer(
            preview,
            parse_mode=ParseMode.MARKDOWN,
            keyboard=kb.pack()
        )


async def handle_after_category(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Вызывается из callback.py после выбора категории кнопкой"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[idea] handle_after_category вызван для chat_id={chat_id}")
    if chat_id not in user_states or user_states[chat_id].get("step") != IdeaStates.WAITING_CATEGORY.value:
        logger.warning(f"[idea] chat_id={chat_id} не в состоянии waiting_category. Состояние: {user_states.get(chat_id)}")
        return

    # Категория уже сохранена в user_states из callback.py
    user_states[chat_id]["step"] = IdeaStates.WAITING_LOCATION.value
    try:
        await event.message.answer(
            "📍 Укажите **местоположение** (адрес, ориентир):",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"[idea] Отправлен запрос местоположения для chat_id={chat_id}")
    except Exception as e:
        logger.error(f"[idea] Ошибка при отправке запроса местоположения для chat_id={chat_id}: {e}")