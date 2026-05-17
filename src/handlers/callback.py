from maxapi.types import MessageCallback, ButtonsPayload, CallbackButton
from maxapi.enums.parse_mode import ParseMode
from maxapi.context import MemoryContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.logging_config import logger
from src.bot.states import IdeaStates, ModerationStates
from src.database.crud import (
    get_initiative_by_id, 
    update_initiative_status,
    get_user_by_id
)
from src.models.initiative import InitiativeStatus, InitiativeCategory
from src.models.user import UserRole

async def handle_callback(callback: MessageCallback, db: AsyncSession, context: MemoryContext):
    """Единый обработчик всех callback-запросов"""
    chat_id = callback.message.recipient.chat_id
    payload = callback.callback.payload
    
    logger.info(f"[handle_callback] Получен callback от chat_id={chat_id}, payload={payload}")
    
    if not payload:
        logger.warning(f"[handle_callback] Пустой payload от chat_id={chat_id}")
        return
    
    # === Модерация: одобрить/отклонить ===
    if payload.startswith("mod_approve:"):
        initiative_id = int(payload.split(":")[1])
        await _handle_moderation_action(callback, db, initiative_id, True)
        
    elif payload.startswith("mod_reject:"):
        initiative_id = int(payload.split(":")[1])
        await context.set_state(ModerationStates.WAITING_REJECT_REASON)
        await context.update_data(initiative_id=initiative_id)
        await callback.answer()
        await callback.message.answer("✍️ Укажите причину отклонения (кратко):")
        
    # === Подача инициативы: выбор категории ===
    elif payload.startswith("cat_select:"):
        category_name = payload.split(":", 1)[1]
        await _handle_category_selected(callback, db, context, category_name)
        
    # === Подтверждение подачи инициативы ===
    elif payload.startswith("idea_confirm:"):
        action = payload.split(":")[1]
        await _handle_idea_confirm(callback, db, context, action)
        
    # === Кнопка "Назад" ===
    elif payload == "cmd_back":
        await context.clear()
        await callback.answer()
        await callback.message.answer("↩️ Возврат в главное меню.\nДоступные команды: /idea, /list, /vote")
    else:
        logger.warning(f"[handle_callback] Неизвестный payload: {payload} для chat_id={chat_id}")

async def _handle_moderation_action(callback: MessageCallback, db: AsyncSession,
                                    initiative_id: int, approve: bool):
    """Обработка решения модератора"""
    chat_id = callback.message.recipient.chat_id
    action = "одобрение" if approve else "отклонение"
    logger.info(f"[_handle_moderation_action] Начало {action} инициативы #{initiative_id} модератором chat_id={chat_id}")

    user = await get_user_by_id(db, chat_id)
    if user is None:
        logger.warning(f"[_handle_moderation_action] Пользователь chat_id={chat_id} не найден в БД")
        await callback.answer("❌ Пользователь не найден", show_alert=True)
        return

    logger.info(f"[_handle_moderation_action] Пользователь chat_id={chat_id} — роль: {user.role}")

    if user.role not in [UserRole.MODERATOR, UserRole.ADMIN]:
        logger.warning(f"[_handle_moderation_action] chat_id={chat_id} не имеет прав (роль={user.role})")
        await callback.answer("❌ Нет прав", show_alert=True)
        return

    initiative = await get_initiative_by_id(db, initiative_id)
    if not initiative:
        logger.warning(f"[_handle_moderation_action] Инициатива #{initiative_id} не найдена в БД")
        await callback.answer("⚠️ Инициатива не найдена", show_alert=True)
        return

    logger.info(f"[_handle_moderation_action] Инициатива #{initiative_id} статус: {initiative.status}")

    if initiative.status != InitiativeStatus.PENDING:
        logger.warning(f"[_handle_moderation_action] Инициатива #{initiative_id} уже обработана (статус={initiative.status})")
        await callback.answer("⚠️ Инициатива уже обработана", show_alert=True)
        return

    if approve:
        await update_initiative_status(db, initiative, InitiativeStatus.APPROVED)
        logger.info(f"[_handle_moderation_action] Инициатива #{initiative_id} статус изменён на APPROVED")
        # await callback.message.answer("✅ Одобрено")
        await callback.message.answer(f"✅ Инициатива #{initiative_id} «{initiative.title}» одобрена.")
        try:
            await callback.bot.send_message(
                chat_id=initiative.author_id,
                text=f"🎉 Ваша инициатива «{initiative.title}» одобрена и опубликована!\n"
                     f"Другие жители могут проголосовать за неё командой /vote {initiative.id}"
            )
            logger.info(f"[_handle_moderation_action] Уведомление автору {initiative.author_id} об одобрении отправлено")
        except Exception as e:
            logger.error(f"[_handle_moderation_action] Ошибка при уведомлении автору {initiative.author_id}: {e}", exc_info=True)
        logger.info(f"[_handle_moderation_action] Инициатива #{initiative_id} одобрена модератором {chat_id}")
    else:
        logger.info(f"[_handle_moderation_action] Одобрение не запрошено — завершение без действий")

async def _handle_category_selected(callback: MessageCallback, db: AsyncSession,
                                    context: MemoryContext, category_name: str):
    """Обработка выбора категории в диалоге подачи инициативы"""
    chat_id = callback.message.recipient.chat_id
    state = await context.get_state()
    logger.info(f"[handle_category_selected] chat_id={chat_id}, category={category_name}, state={state}")
    
    if state != IdeaStates.WAITING_CATEGORY:
        logger.warning(f"[handle_category_selected] Неверное состояние {state} для chat_id={chat_id}")
        await callback.answer()
        return
    
    await context.update_data(category=category_name)
    await context.set_state(IdeaStates.WAITING_LOCATION)
    await callback.answer()
    await callback.message.answer("📍 Укажите **местоположение** (адрес, ориентир):", parse_mode=ParseMode.MARKDOWN)

async def _handle_idea_confirm(callback: MessageCallback, db: AsyncSession,
                                context: MemoryContext, action: str):
    """Финальное подтверждение/отмена подачи инициативы"""
    chat_id = callback.message.recipient.chat_id
    logger.info(f"[handle_idea_confirm] Вызван для chat_id={chat_id}, action={action}")
    
    state = await context.get_state()
    logger.info(f"[handle_idea_confirm] Текущее состояние: {state}")
    
    if state != IdeaStates.CONFIRM_SUBMIT:
        logger.warning(f"[handle_idea_confirm] Неверное состояние {state} для chat_id={chat_id}, ожидалось confirm_submit")
        await callback.answer()
        return
    
    await callback.answer()
    
    if action == "no":
        logger.info(f"[handle_idea_confirm] Пользователь {chat_id} отменил подачу")
        await context.clear()
        await callback.message.answer("❌ Подача инициативы отменена.")
        return
    
    logger.info(f"[handle_idea_confirm] Пользователь {chat_id} подтверждает отправку")
    data = await context.get_data()
    logger.info(f"[handle_idea_confirm] Данные из контекста: {data}")
    
    # Создаём инициативу
    from src.database.crud import create_initiative
    from src.services.notification import notify_moderators
    
    await context.clear()
    logger.info(f"[handle_idea_confirm] Создаём инициативу с данными: {data}")
    try:
        category_enum = InitiativeCategory(data["category"])
        logger.info(f"Category enum: {category_enum}, value: {category_enum.value}")
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверная категория")
        return
    
    initiative = await create_initiative(
        db=db,
        author_id=callback.message.recipient.chat_id,
        title=data["title"],
        description=data["description"],
        category=category_enum,
        location=data["location"]
    )
    logger.info(f"[handle_idea_confirm] Инициатива создана с ID={initiative.id}")
    
    await callback.message.answer(
        f"✅ Инициатива #{initiative.id} отправлена на модерацию!\n"
        f"Вы получите уведомление о решении."
    )
    
    await notify_moderators(db, callback.bot, initiative)
    logger.info(f"[handle_idea_confirm] Инициатива #{initiative.id} уведомлена модераторов")