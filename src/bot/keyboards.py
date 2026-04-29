from maxapi.types import InlineKeyboardBuilder, CallbackButton

def make_moderation_keyboard(initiative_id: int) -> InlineKeyboardBuilder:
    """Inline-клавиатура для модератора: ✅ Одобрить / ❌ Отклонить"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Одобрить", payload=f"mod_approve:{initiative_id}"),
        CallbackButton(text="❌ Отклонить", payload=f"mod_reject:{initiative_id}")
    )
    return builder

def make_category_keyboard() -> InlineKeyboardBuilder:
    """Клавиатура с категориями для выбора"""
    builder = InlineKeyboardBuilder()
    categories = ["дороги", "благоустройство", "детские площадки", "освещение", "ЖКХ"]
    
    # По 2 кнопки в ряду
    for i in range(0, len(categories), 2):
        row_buttons = []
        for cat in categories[i:i+2]:
            row_buttons.append(CallbackButton(text=cat, payload=f"cat_select:{cat}"))
        builder.row(*row_buttons)
    
    return builder

def make_confirm_keyboard() -> InlineKeyboardBuilder:
    """Кнопки подтверждения/отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        CallbackButton(text="✅ Да, отправить", payload="idea_confirm:yes"),
        CallbackButton(text="❌ Нет, отменить", payload="idea_confirm:no")
    )
    return builder

def make_back_keyboard() -> InlineKeyboardBuilder:
    """Кнопка «Назад»"""
    builder = InlineKeyboardBuilder()
    builder.row(CallbackButton(text="⬅️ Назад", payload="cmd_back"))
    return builder