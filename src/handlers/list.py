from maxapi.types import MessageCreated, Command
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import get_approved_initiatives
from src.models.initiative import InitiativeCategory

async def handle_list(event: MessageCreated, db: AsyncSession):
    """Обработка команды /list — показ одобренных инициатив"""
    chat_id = event.message.recipient.chat_id
    text = event.message.text.strip()
    
    # Парсинг категории из команды: /list дороги
    parts = text.split(maxsplit=1)
    category_name = parts[1].lower() if len(parts) > 1 else None
    
    category = None
    if category_name:
        try:
            category = InitiativeCategory(category_name)
        except ValueError:
            await event.message.answer(
                f"❌ Неизвестная категория: {category_name}\n"
                f"Доступные: {', '.join(c.value for c in InitiativeCategory)}"
            )
            return
    
    initiatives = await get_approved_initiatives(db, category=category)
    
    if not initiatives:
        await event.message.answer(
            "📭 Пока нет одобренных инициатив" + 
            (f" в категории «{category.value}»" if category else "") +
            ".\nСтаньте первым — подайте свою идею командой /idea!"
        )
        return
    
    # Формируем список с нумерацией
    lines = [f"📋 **Одобренные инициативы**{' | ' + category.value if category else ''}:\n"]
    for i, init in enumerate(initiatives, 1):
        lines.append(
            f"{i}. **{init.title}** (#{init.id})\n"
            f"   📍 {init.location}\n"
            f"   👍 Голосов: {init.votes_count}\n"
            f"   /vote {init.id} — проголосовать"
        )
    
    await event.message.answer("\n\n".join(lines), parse_mode="Markdown")
    logger.info(f"Пользователь {chat_id} запросил список инициатив")