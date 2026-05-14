from maxapi.types import MessageCreated
from maxapi.enums.parse_mode import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import get_approved_initiatives

async def handle_list(event: MessageCreated, db: AsyncSession):
    """Обработка команды /list — показ всех одобренных инициатив"""
    chat_id = event.message.recipient.chat_id
    logger.info(f"[list] handle_list: chat_id={chat_id}")
    
    logger.info(f"[list] запрос к БД: get_approved_initiatives")
    initiatives = await get_approved_initiatives(db)
    logger.info(f"[list] получено {len(initiatives)} инициатив")
    
    if not initiatives:
        await event.message.answer(
            "📭 Пока нет одобренных инициатив.\n"
            "Станьте первым — подайте свою идею командой /idea!"
        )
        return
    
    lines = ["📋 **Одобренные инициативы:**\n"]
    for i, init in enumerate(initiatives, 1):
        lines.append(
            f"{i}. **{init.title}** (#{init.id})\n"
            f"   📍 {init.location}\n"
            f"   👍 Голосов: {init.votes_count}\n"
            f"   /vote {init.id} — проголосовать"
        )
    
    await event.message.answer("\n\n".join(lines), parse_mode=ParseMode.MARKDOWN)
    logger.info(f"[list] ответ отправлен пользователю {chat_id}")