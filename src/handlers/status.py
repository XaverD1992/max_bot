import re
from maxapi.types import MessageCreated
from maxapi.enums.parse_mode import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import get_user_initiatives, get_initiative_by_id
from src.models.initiative import InitiativeStatus
from src.bot.keyboards import make_commands_keyboard

STATUS_LABELS = {
    InitiativeStatus.PENDING: "🕒 На модерации",
    InitiativeStatus.APPROVED: "✅ Одобрена",
    InitiativeStatus.REJECTED: "❌ Отклонена",
    InitiativeStatus.IN_PROGRESS: "🚧 Реализуется",
    InitiativeStatus.COMPLETED: "🏁 Завершена",
}

async def handle_status(event: MessageCreated, db: AsyncSession):
    """Обработка команды /status — показ статуса инициативы"""
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip() if event.message.body.text else ""
    
    initiative = None
    
    if re.match(r"^\d+$", text):
        # Сырой номер из FSM (без префикса команды)
        initiative_id = int(text)
        initiative = await get_initiative_by_id(db, initiative_id)
        if not initiative:
            await event.message.answer(f"❌ Инициатива #{initiative_id} не найдена")
            await event.message.answer("📋 Доступные команды:", keyboard=make_commands_keyboard())
            return
    else:
        match = re.match(r"^/status\s*(\d+)?$", text, re.I)
        if match and match.group(1):
            initiative_id = int(match.group(1))
            initiative = await get_initiative_by_id(db, initiative_id)
            if not initiative:
                await event.message.answer(f"❌ Инициатива #{initiative_id} не найдена")
                await event.message.answer("📋 Доступные команды:", keyboard=make_commands_keyboard())
                return
        else:
            initiative = None
    
    if initiative is None:
        initiatives = await get_user_initiatives(db, chat_id, limit=1)
        if not initiatives:
            await event.message.answer("📭 Вы ещё не подавали инициативы. Используйте /idea")
            await event.message.answer("📋 Доступные команды:", keyboard=make_commands_keyboard())
            return
        initiative = initiatives[0]
    
    status_label = STATUS_LABELS.get(initiative.status, initiative.status.value)
    
    lines = [
        f"📊 **Статус инициативы #{initiative.id}**",
        f"   📝 {initiative.title}",
        f"   {status_label}",
    ]
    
    if initiative.status == InitiativeStatus.REJECTED and initiative.reject_reason:
        lines.append(f"   📌 Причина: {initiative.reject_reason}")
    
    lines.append(f"   👍 Голосов: {initiative.votes_count}")
    
    await event.message.answer("\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    await event.message.answer("📋 Доступные команды:", keyboard=make_commands_keyboard())
    logger.info(f"[status] Инициатива #{initiative.id} пользователю {chat_id}: {status_label}")
