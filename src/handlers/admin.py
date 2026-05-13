from maxapi.types import MessageCreated, Command
from sqlalchemy.ext.asyncio import AsyncSession
from src.config import settings
from src.logging_config import logger
from src.database.crud import get_user_by_id, set_user_role
from src.models.user import UserRole

async def handle_set_role(event: MessageCreated, db: AsyncSession):
    """Админ-команда: /set_role @username moderator|admin|resident"""
    chat_id = event.message.recipient.chat_id
    
    # Проверка: только админы из ADMIN_USER_IDS
    if chat_id not in settings.ADMIN_USER_IDS:
        await event.message.answer("❌ У вас нет прав для этой команды")
        return
    
    text = event.message.text.strip()
    parts = text.split()
    
    if len(parts) != 3:
        await event.message.answer(
            "Использование: `/set_role <chat_id> <role>`\n"
            "Роли: resident, moderator, admin",
            parse_mode="Markdown"
        )
        return
    
    try:
        target_chat_id = int(parts[1])
        role_name = parts[2].lower()
        role = UserRole(role_name)
    except (ValueError, KeyError):
        await event.message.answer(
            "❌ Ошибка: chat_id должен быть числом, а роль — одной из: resident, moderator, admin"
        )
        return
    
    user = await get_user_by_id(db, target_chat_id)
    if not user:
        await event.message.answer(f"❌ Пользователь {target_chat_id} не найден в базе")
        return
    
    await set_user_role(db, target_chat_id, role)
    await event.message.answer(f"✅ Пользователю {target_chat_id} назначена роль: {role.value}")
    logger.info(f"Админ {chat_id} изменил роль пользователя {target_chat_id} на {role.value}")