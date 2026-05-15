"""
Обработчики, связанные с модерацией инициатив.
- Обработка причины отклонения (текстовый ввод после нажатия ❌)
- Вспомогательные функции для уведомлений
"""
import logging
from maxapi.types import MessageCreated
from maxapi.context import MemoryContext
from sqlalchemy.ext.asyncio import AsyncSession

from src.logging_config import logger
from src.database.crud import (
    get_initiative_by_id,
    update_initiative_status,
    get_user_by_id
)
from src.bot.states import ModerationStates
from src.models.initiative import InitiativeStatus
from src.models.user import UserRole

logger = logging.getLogger(__name__)


async def handle_reject_reason(event: MessageCreated, db: AsyncSession, context: MemoryContext):
    """
    Обработка ввода причины отклонения инициативы.
    
    Вызывается, когда модератор нажал ❌, и бот ожидает текстовую причину.
    """
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip() if event.message.body.text else ""
    
    logger.info(f"[handle_reject_reason] START: chat_id={chat_id}, text_length={len(text)}")
    
    state = await context.get_state()
    logger.info(f"[handle_reject_reason] Current state: {state}")
    
    if state != ModerationStates.WAITING_REJECT_REASON:
        logger.warning(f"[handle_reject_reason] WRONG_STATE: expected {ModerationStates.WAITING_REJECT_REASON}, got {state}")
        return
    
    logger.info(f"[handle_reject_reason] State check passed")
    
    data = await context.get_data()
    logger.info(f"[handle_reject_reason] Context data: {data}")
    
    initiative_id = data.get("initiative_id")
    if not initiative_id:
        logger.error(f"[handle_reject_reason] NO_INITIATIVE_ID in context")
        await event.message.answer("❌ Ошибка: не указан номер инициативы")
        await context.clear()
        return
    
    logger.info(f"[handle_reject_reason] Initiative ID: {initiative_id}")
    
    # Получаем инициативу
    logger.info(f"[handle_reject_reason] Fetching initiative from DB...")
    initiative = await get_initiative_by_id(db, initiative_id)
    if not initiative:
        logger.error(f"[handle_reject_reason] Initiative #{initiative_id} NOT FOUND")
        await event.message.answer("❌ Инициатива не найдена (возможно, уже обработана)")
        await context.clear()
        return
    
    logger.info(f"[handle_reject_reason] Initiative found: title='{initiative.title}', status={initiative.status}")
    
    # Проверяем, что инициатива ещё на модерации
    if initiative.status != InitiativeStatus.PENDING:
        logger.warning(f"[handle_reject_reason] Initiative already processed, status={initiative.status}")
        await event.message.answer("⚠️ Эта инициатива уже была обработана")
        await context.clear()
        return
    
    logger.info(f"[handle_reject_reason] Status check passed (PENDING)")
    
    # Проверяем роль (на всякий случай)
    logger.info(f"[handle_reject_reason] Checking user role for chat_id={chat_id}")
    user = await get_user_by_id(db, chat_id)
    if user and user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        logger.warning(f"[handle_reject_reason] INSUFFICIENT_PERMISSIONS: role={user.role}")
        await event.message.answer("❌ У вас нет прав для этого действия")
        return
    
    logger.info(f"[handle_reject_reason] Permission check passed, user role={user.role if user else 'None'}")
    
    # Сохраняем причину и меняем статус
    reason = text[:500]  # Ограничиваем длину
    logger.info(f"[handle_reject_reason] Rejecting with reason: '{reason[:100]}...'")
    
    await update_initiative_status(db, initiative, InitiativeStatus.REJECTED)
    logger.info(f"[handle_reject_reason] Initiative #{initiative_id} status updated to REJECTED")
    
    # Очищаем состояние
    await context.clear()
    logger.info(f"[handle_reject_reason] Context cleared")
    
    # Уведомляем модератора
    await event.message.answer(
        f"❌ Инициатива #{initiative.id} «{initiative.title}» отклонена.\n"
        f"Автору отправлено уведомление."
    )
    logger.info(f"[handle_reject_reason] Moderator notified")
    
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