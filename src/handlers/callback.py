from maxapi.types import MessageCallback, ButtonsPayload, CallbackButton
from maxapi.enums.parse_mode import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.database.crud import (
    get_initiative_by_id, 
    update_initiative_status,
    get_user_by_id
)
from src.models.initiative import InitiativeStatus, InitiativeCategory
from src.models.user import UserRole
from src.bot.states import IdeaStates

async def handle_callback(callback: MessageCallback, db: AsyncSession, user_states: dict):
    """Единый обработчик всех callback-запросов"""
    chat_id = callback.message.recipient.chat_id
    payload = callback.payload
    
    if not payload:
        return
    
    # === Модерация: одобрить/отклонить ===
    if payload.startswith("mod_approve:"):
        initiative_id = int(payload.split(":")[1])
        await _handle_moderation_action(callback, db, initiative_id, True)
        
    elif payload.startswith("mod_reject:"):
        initiative_id = int(payload.split(":")[1])
        # Запрашиваем причину отклонения
        user_states[chat_id] = {"step": "waiting_reject_reason", "initiative_id": initiative_id}
        await callback.answer()  # Убираем "часики"
        await callback.message.answer("✍️ Укажите причину отклонения (кратко):")
        
    # === Подача инициативы: выбор категории ===
    elif payload.startswith("cat_select:"):
        category_name = payload.split(":", 1)[1]
        await _handle_category_selected(callback, db, user_states, category_name)
        
    # === Подтверждение подачи инициативы ===
    elif payload.startswith("idea_confirm:"):
        action = payload.split(":")[1]
        await _handle_idea_confirm(callback, db, user_states, action)
        
    # === Кнопка "Назад" ===
    elif payload == "cmd_back":
        if chat_id in user_states:
            del user_states[chat_id]
        await callback.answer()
        await callback.message.answer("↩️ Возврат в главное меню.\nДоступные команды: /idea, /list, /vote")

async def _handle_moderation_action(callback: MessageCallback, db: AsyncSession,
                                   initiative_id: int, approve: bool):
    """Обработка решения модератора"""
    chat_id = callback.message.recipient.chat_id
    user = await get_user_by_id(db, chat_id)
    
    if user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        await callback.answer("❌ Нет прав", show_alert=True)
        return
    
    initiative = await get_initiative_by_id(db, initiative_id)
    if not initiative or initiative.status != InitiativeStatus.PENDING:
        await callback.answer("⚠️ Инициатива уже обработана", show_alert=True)
        return
    
    if approve:
        await update_initiative_status(db, initiative, InitiativeStatus.APPROVED)
        await callback.answer("✅ Одобрено")
        # Уведомляем автора
        await callback.bot.send_message(
            chat_id=initiative.author_id,
            text=f"🎉 Ваша инициатива «{initiative.title}» одобрена и опубликована!\n"
                 f"Другие жители могут проголосовать за неё командой /vote {initiative.id}"
        )
        logger.info(f"Инициатива #{initiative_id} одобрена модератором {chat_id}")
    else:
        # Отклонение обрабатывается в handle_callback (запрос причины)
        pass

async def _handle_category_selected(callback: MessageCallback, db: AsyncSession,
                                   user_states: dict, category_name: str):
    """Обработка выбора категории в диалоге подачи инициативы"""
    chat_id = callback.message.recipient.chat_id
    if chat_id not in user_states or user_states[chat_id].get("step") != IdeaStates.WAITING_CATEGORY.value:
        await callback.answer()
        return
    
    user_states[chat_id]["category"] = category_name
    user_states[chat_id]["step"] = IdeaStates.WAITING_LOCATION.value
    await callback.answer()
    await callback.message.answer("📍 Укажите **местоположение** (адрес, ориентир):", parse_mode=ParseMode.MARKDOWN)

async def _handle_idea_confirm(callback: MessageCallback, db: AsyncSession,
                               user_states: dict, action: str):
    """Финальное подтверждение/отмена подачи инициативы"""
    chat_id = callback.message.recipient.chat_id
    if chat_id not in user_states or user_states[chat_id].get("step") != IdeaStates.CONFIRM_SUBMIT.value:
        await callback.answer()
        return
    
    await callback.answer()
    
    if action == "no":
        del user_states[chat_id]
        await callback.message.answer("❌ Подача инициативы отменена.")
        return
    
    # Создаём инициативу
    from src.database.crud import create_initiative
    from src.services.notification import notify_moderators
    
    data = user_states.pop(chat_id)
    logger.info(f"Confirming idea with data: {data}")
    try:
        category_enum = InitiativeCategory(data["category"])
        logger.info(f"Category enum: {category_enum}, value: {category_enum.value}")
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверная категория")
        return
    
    initiative = await create_initiative(
        db=db,
        author_id=chat_id,
        title=data["title"],
        description=data["description"],
        category=category_enum,
        location=data["location"]
    )
    
    await callback.message.answer(
        f"✅ Инициатива #{initiative.id} отправлена на модерацию!\n"
        f"Вы получите уведомление о решении."
    )
    
    # Уведомляем модераторов
    await notify_moderators(db, callback.bot, initiative)
    logger.info(f"Инициатива #{initiative.id} отправлена на модерацию")