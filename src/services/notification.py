from sqlalchemy.ext.asyncio import AsyncSession
from maxapi import Bot
from src.database.crud import get_moderators
from src.models.initiative import Initiative
from src.bot.keyboards import make_moderation_keyboard

async def notify_moderators(db: AsyncSession, bot: Bot, initiative: Initiative):
    """Отправить уведомление всем модераторам о новой инициативе"""
    moderators = await get_moderators(db)
    if not moderators:
        return
    
    preview = (
        f"🔔 **Новая инициатива на модерации**\n\n"
        f"📌 *{initiative.title}*\n"
        f"📝 {initiative.description[:300]}{'...' if len(initiative.description) > 300 else ''}\n"
        f"🏷️ Категория: {initiative.category.value}\n"
        f"📍 Адрес: {initiative.location}\n"
        f"👤 Автор: {initiative.author_id}\n\n"
        f"Примите решение:"
    )
    
    keyboard = make_moderation_keyboard(initiative.id)
    
    for mod in moderators:
        try:
            await bot.send_message(
                chat_id=mod.id,
                text=preview,
                attachments=[keyboard],
                parse_mode="Markdown"
            )
        except Exception as e:
            # Логгируем, но не прерываем отправку остальным
            from src.logging_config import logger
            logger.error(f"Не удалось отправить уведомление модератору {mod.id}: {e}")