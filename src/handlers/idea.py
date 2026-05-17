"""
Пошаговый диалог подачи инициативы.
Работает в паре с callback.py (выбор категории и подтверждение).
"""
from maxapi.types import MessageCreated
from maxapi.enums.parse_mode import ParseMode
from maxapi.context import MemoryContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.bot.keyboards import make_category_keyboard, make_confirm_keyboard
from src.bot.states import IdeaStates

async def handle_idea_start(event: MessageCreated, db: AsyncSession, context: MemoryContext):
    """Запуск диалога подачи инициативы"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[idea] handle_idea_start вызван для chat_id={chat_id}")

    await context.set_state(IdeaStates.WAITING_TITLE)
    try:
        await event.message.answer(
            "✍️ Введите **название** инициативы (кратко, 1-2 строки):"
        )
        logger.info(f"[idea] Отправлено сообщение с запросом названия для chat_id={chat_id}")
    except Exception as e:
        logger.error(f"[idea] Ошибка при отправке сообщения для chat_id={chat_id}: {e}")


async def handle_idea_step(event: MessageCreated, db: AsyncSession, context: MemoryContext):
    """Обработка текстовых шагов диалога"""
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip() if event.message.body.text else ""

    state = await context.get_state()
    logger.info(f"[idea] handle_idea_step вызван для chat_id={chat_id}, state={state}, text='{text[:30]}...'")

    if state == IdeaStates.WAITING_TITLE:
        if len(text) < 3:
            await event.message.answer("❌ Название слишком короткое. Попробуйте снова.")
            return
        await context.update_data(title=text)
        await context.set_state(IdeaStates.WAITING_DESCRIPTION)
        await event.message.answer(
            "📝 Теперь введите **описание** проблемы или предложения (подробно):",
            parse_mode=ParseMode.MARKDOWN
        )

    elif state == IdeaStates.WAITING_DESCRIPTION:
        if len(text) < 10:
            await event.message.answer("❌ Описание слишком короткое. Добавьте деталей.")
            return
        await context.update_data(description=text)
        await context.set_state(IdeaStates.WAITING_CATEGORY)
        
        kb = make_category_keyboard()
        await event.message.answer(
            "🏷️ Выберите **категорию**:",
            attachments=[kb.pack()],
            parse_mode=ParseMode.MARKDOWN
        )

    elif state == IdeaStates.WAITING_LOCATION:
        if len(text) < 5:
            await event.message.answer("❌ Укажите адрес подробнее (улица, дом, ориентир).")
            return
        await context.update_data(location=text)
        await context.set_state(IdeaStates.CONFIRM_SUBMIT)
        
        data = await context.get_data()
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
            attachments=[kb.pack()],
            parse_mode=ParseMode.MARKDOWN
        )


async def handle_after_category(event: MessageCreated, db: AsyncSession, context: MemoryContext):
    """Вызывается из callback.py после выбора категории кнопкой"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[idea] handle_after_category вызван для chat_id={chat_id}")
    
    state = await context.get_state()
    if state != IdeaStates.WAITING_CATEGORY:
        logger.warning(f"[idea] chat_id={chat_id} не в состоянии waiting_category.")
        return
    
    await context.set_state(IdeaStates.WAITING_LOCATION)
    try:
        await event.message.answer(
            "📍 Укажите **местоположение** (адрес, ориентир):",
            parse_mode=ParseMode.MARKDOWN
        )
        logger.info(f"[idea] Отправлен запрос местоположения для chat_id={chat_id}")
    except Exception as e:
        logger.error(f"[idea] Ошибка при отправке запроса местоположения для chat_id={chat_id}: {e}")