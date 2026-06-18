from maxapi.types import ButtonsPayload, CallbackButton

COMMANDS_HELP = (
    "📋 Доступные команды:\n"
    "/idea — подать инициативу\n"
    "/list — посмотреть одобренные инициативы\n"
    "/vote [номер] — проголосовать\n"
    "/status — статус последней инициативы\n"
    "/status [номер] — статус конкретной инициативы"
)

def make_commands_keyboard() -> ButtonsPayload:
    """Инлайн-клавиатура со всеми командами бота"""
    buttons = [
        [CallbackButton(text="/idea — подать инициативу", payload="cmd:/idea")],
        [CallbackButton(text="/list — посмотреть одобренные инициативы", payload="cmd:/list")],
        [CallbackButton(text="/vote — проголосовать", payload="input:/vote")],
        [CallbackButton(text="/status — статус последней инициативы", payload="cmd:/status")],
        [CallbackButton(text="/status [номер] — статус конкретной инициативы", payload="input:/status")],
    ]
    return ButtonsPayload(buttons=buttons)

def make_moderation_keyboard(initiative_id: int) -> ButtonsPayload:
    """Inline-клавиатура для модератора: ✅ Одобрить / ❌ Отклонить"""
    buttons = [
        [
            CallbackButton(text="✅ Одобрить", payload=f"mod_approve:{initiative_id}"),
            CallbackButton(text="❌ Отклонить", payload=f"mod_reject:{initiative_id}")
        ]
    ]
    return ButtonsPayload(buttons=buttons)

def make_category_keyboard() -> ButtonsPayload:
    """Клавиатура с категориями для выбора"""
    categories = ["дороги", "благоустройство", "детские площадки", "освещение", "ЖКХ"]
    buttons = []
    for i in range(0, len(categories), 2):
        row = []
        for cat in categories[i:i+2]:
            row.append(CallbackButton(text=cat, payload=f"cat_select:{cat}"))
        buttons.append(row)
    return ButtonsPayload(buttons=buttons)

def make_confirm_keyboard() -> ButtonsPayload:
    """Кнопки подтверждения/отмены"""
    buttons = [
        [
            CallbackButton(text="✅ Да, отправить", payload="idea_confirm:yes"),
            CallbackButton(text="❌ Нет, отменить", payload="idea_confirm:no")
        ]
    ]
    return ButtonsPayload(buttons=buttons)

def make_back_keyboard() -> ButtonsPayload:
    """Кнопка «Назад»"""
    buttons = [
        [CallbackButton(text="⬅️ Назад", payload="cmd_back")]
    ]
    return ButtonsPayload(buttons=buttons)