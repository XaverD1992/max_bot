"""
Обработчики, связанные с модерацией инициатив.
- Обработка причины отклонения (текстовый ввод после нажатия ❌)
- Вспомогательные функции для уведомлений
"""
import logging
from maxapi.types import MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.database.crud import (
    get_initiative_by_id,
    update_initiative_status,
    get_user_by_id
)
from src.models.initiative import InitiativeStatus
from src.models.user import UserRole

logger = logging.getLogger(__name__)


async def handle_reject_reason(event: MessageCreated, db: AsyncSession, user_states: dict):
    """
    Обработка ввода причины отклонения инициативы.
    
    Вызывается, когда модератор нажал ❌, и бот ожидает текстовую причину.
    """
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip() if event.message.body.text else ""
    
    # Проверяем, что пользователь в правильном состоянии
    if chat_id not in user_states:
        return
    
    state = user_states[chat_id]
    if state.get("step") != "waiting_reject_reason":
        return
    
    initiative_id = state.get("initiative_id")
    if not initiative_id:
        await event.message.answer("❌ Ошибка: не указан номер инициативы")
        del user_states[chat_id]
        return
    
    # Получаем инициативу
    initiative = await get_initiative_by_id(db, initiative_id)
    if not initiative:
        await event.message.answer("❌ Инициатива не найдена (возможно, уже обработана)")
        del user_states[chat_id]
        return
    
    # Проверяем, что инициатива ещё на модерации
    if initiative.status != InitiativeStatus.PENDING:
        await event.message.answer("⚠️ Эта инициатива уже была обработана")
        del user_states[chat_id]
        return
    
    # Проверяем роль (на всякий случай)
    user = await get_user_by_id(db, chat_id)
    if user and user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        await event.message.answer("❌ У вас нет прав для этого действия")
        return
    
    # Сохраняем причину и меняем статус
    reason = text[:500]  # Ограничиваем длину
    await update_initiative_status(db, initiative, InitiativeStatus.REJECTED)
    
    # Очищаем состояние
    del user_states[chat_id]
    
    # Уведомляем модератора
    await event.message.answer(
        f"❌ Инициатива #{initiative.id} «{initiative.title}» отклонена.\n"
        f"Автору отправлено уведомление."
    )
    
    # Уведомляем автора инициативы
    try:
        await event.bot.send_message(
            chat_id=initiative.author_id,
            text=(
                f"❌ Ваша инициатива «{initiative.title}» отклонена модератором.\n\n"
                f"📝 Причина: {reason}\n\n"
                f"Вы можете подать новую инициативу командой /idea"
            )
        )
        logger.info(
            f"Инициатива #{initiative_id} отклонена модератором {chat_id}. "
            f"Автор {initiative.author_id} уведомлён. Причина: {reason}"
        )
    except Exception as e:
        logger.error(
            f"Не удалось отправить уведомление автору {initiative.author_id} "
            f"об отклонении инициативы #{initiative_id}: {e}"
        )
        # Не прерываем выполнение, т.к. статус уже изменён в БД


async def handle_moderation_timeout(db: AsyncSession, initiative_id: int):
    """
    Опционально: обработка таймаута модерации.
    
    Можно вызвать по расписанию (cron) для инициатив, 
    которые висят на модерации слишком долго.
    """
    initiative = await get_initiative_by_id(db, initiative_id)
    if not initiative or initiative.status != InitiativeStatus.PENDING:
        return False
    
    # Пока просто логируем — в MVP не реализуем авто-действия
    logger.warning(f"Инициатива #{initiative_id} ожидает модерации более 24 часов")
    return True