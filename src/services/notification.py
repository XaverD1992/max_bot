from sqlalchemy.ext.asyncio import AsyncSession
from maxapi import Bot
from maxapi.enums.parse_mode import ParseMode
from src.database.crud import get_moderators
from src.models.initiative import Initiative
from src.bot.keyboards import make_moderation_keyboard
from src.logging_config import logger

async def notify_moderators(db: AsyncSession, bot: Bot, initiative: Initiative):
    """Отправить уведомление всем модераторам о новой инициативе"""

    logger.info(f"Вход в функцию уведомления модераторов")
    
    moderators = await get_moderators(db)
    if not moderators:
        logger.info(f"Модераторы не найдены")
        return
    
    logger.info(f"Найдено {len(moderators)} модераторов: {[mod.id for mod in moderators]}")
    
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
    logger.debug(f"Сформирована клавиатура для инициативы {initiative.id}")
    logger.debug(f"Текст превью: {repr(preview[:100])}...")
    
    for mod in moderators:
        try:
            logger.debug(f"Попытка отправки уведомления модератору {mod.id} (chat_id={mod.id})")
            result = await bot.send_message(
                chat_id=mod.id,
                text=preview,
                attachments=[keyboard.pack()],  # ИСПРАВЛЕНО: нужно использовать .pack()
                parse_mode=ParseMode.MARKDOWN
            )
            logger.debug(f"Результат отправки модератору {mod.id}: {result}")
            logger.info(f"Уведомление успешно отправлено модератору {mod.id}")
        except Exception as e:
            # Логгируем, но не прерываем отправку остальным
            logger.error(f"Не удалось отправить уведомление модератору {mod.id}: {e}", exc_info=True)
            logger.error(f"Тип ошибки: {type(e).__name__}")