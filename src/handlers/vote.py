import re
from maxapi.types import MessageCreated, Command
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import (
    get_initiative_by_id, 
    has_user_voted, 
    add_vote,
    get_or_create_user
)
from src.models.initiative import InitiativeStatus

async def handle_vote(event: MessageCreated, db: AsyncSession):
    """Обработка команды /vote [id] — голосование за инициативу"""
    chat_id = event.message.chat_id
    text = event.message.text.strip()
    
    # Парсим номер инициативы: /vote 123
    match = re.match(r"^/vote\s+(\d+)$", text, re.I)
    if not match:
        await event.message.answer(
            "❌ Неверный формат.\nИспользуйте: `/vote 123` (где 123 — номер инициативы)",
            parse_mode="Markdown"
        )
        return
    
    initiative_id = int(match.group(1))
    initiative = await get_initiative_by_id(db, initiative_id)
    
    if not initiative:
        await event.message.answer(f"❌ Инициатива #{initiative_id} не найдена")
        return
    
    if initiative.status != InitiativeStatus.APPROVED:
        await event.message.answer(
            "⚠️ За эту инициативу нельзя проголосовать "
            "(она ещё не одобрена или отклонена)"
        )
        return
    
    # Получаем или создаём пользователя
    user = await get_or_create_user(db, chat_id)
    
    # Проверяем, не голосовал ли уже
    if await has_user_voted(db, chat_id, initiative_id):
        await event.message.answer(
            f"✅ Вы уже проголосовали за «{initiative.title}».\n"
            f"Текущий счёт: {initiative.votes_count} голосов"
        )
        return
    
    # Добавляем голос
    success = await add_vote(db, chat_id, initiative_id)
    if success:
        await event.message.answer(
            f"✅ Ваш голос за «{initiative.title}» принят!\n"
            f"📊 Всего голосов: {initiative.votes_count + 1}"
        )
        logger.info(f"Голос от {chat_id} за инициативу #{initiative_id}")
    else:
        await event.message.answer("❌ Не удалось записать голос. Попробуйте позже.")