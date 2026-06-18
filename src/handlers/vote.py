import re
from maxapi.types import MessageCreated, Command
from maxapi.enums.parse_mode import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import (
    get_initiative_by_id, 
    has_user_voted, 
    add_vote,
    get_or_create_user
)
from src.models.initiative import InitiativeStatus
from src.bot.keyboards import make_commands_keyboard

async def handle_vote(event: MessageCreated, db: AsyncSession):
    """Обработка команды /vote [id] — голосование за инициативу"""
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text.strip() if event.message.body.text else ""
    
    if re.match(r"^\d+$", text):
        initiative_id = int(text)
    else:
        match = re.match(r"^/vote\s+(\d+)$", text, re.I)
        if not match:
            await event.message.answer(
                "❌ Неверный формат.\nИспользуйте: `/vote 123` (где 123 — номер инициативы)",
                parse_mode=ParseMode.MARKDOWN
            )
            await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])
            return
        initiative_id = int(match.group(1))
    
    initiative = await get_initiative_by_id(db, initiative_id)
    
    if not initiative:
        await event.message.answer(f"❌ Инициатива #{initiative_id} не найдена")
        await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])
        return
    
    if initiative.status != InitiativeStatus.APPROVED:
        await event.message.answer(
            "⚠️ За эту инициативу нельзя проголосовать "
            "(она ещё не одобрена или отклонена)"
        )
        await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])
        return
    
    # Получаем или создаём пользователя
    user = await get_or_create_user(db, chat_id)
    
    # Проверяем, не голосовал ли уже
    if await has_user_voted(db, chat_id, initiative_id):
        await event.message.answer(
            f"✅ Вы уже проголосовали за «{initiative.title}».\n"
            f"Текущий счёт: {initiative.votes_count} голосов"
        )
        await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])
        return
    
    # Добавляем голос
    success = await add_vote(db, chat_id, initiative_id)
    if success:
        await event.message.answer(
            f"✅ Ваш голос за «{initiative.title}» принят!\n"
            f"📊 Всего голосов: {initiative.votes_count + 1}"
        )
        await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])
        logger.info(f"Голос от {chat_id} за инициативу #{initiative_id}")
    else:
        await event.message.answer("❌ Не удалось записать голос. Попробуйте позже.")
        await event.message.answer("📋 Доступные команды:", attachments=[make_commands_keyboard().pack()])