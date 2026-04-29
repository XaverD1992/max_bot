"""
Пошаговый диалог подачи инициативы.
Работает в паре с callback.py (выбор категории и подтверждение).
"""
from maxapi.types import MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.bot.states import IdeaStates
from src.bot.keyboards import make_category_keyboard, make_confirm_keyboard

async def handle_idea_start(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Запуск диалога подачи инициативы"""
    chat_id = event.message.chat_id
    
    # Инициализируем состояние
    user_states[chat_id] = {"step": IdeaStates.WAITING_TITLE.value}
    await event.message.answer(
        "✍️ Введите **название** инициативы (кратко, 1-2 строки):",
        parse_mode="Markdown"
    )


async def handle_idea_step(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Обработка текстовых шагов диалога"""
    chat_id = event.message.chat_id
    text = event.message.text.strip()

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
            parse_mode="Markdown"
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
            keyboard=kb.as_markup()
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
            parse_mode="Markdown",
            keyboard=kb.as_markup()
        )


async def handle_after_category(event: MessageCreated, db: AsyncSession, user_states: dict):
    """Вызывается из callback.py после выбора категории кнопкой"""
    chat_id = event.message.chat_id
    if chat_id not in user_states or user_states[chat_id].get("step") != IdeaStates.WAITING_CATEGORY.value:
        return
    
    # Категория уже сохранена в user_states из callback.py
    user_states[chat_id]["step"] = IdeaStates.WAITING_LOCATION.value
    await event.message.answer(
        "📍 Укажите **местоположение** (адрес, ориентир):",
        parse_mode="Markdown"
    )