"""Состояния для пошагового диалога подачи инициативы"""
from maxapi.context import State, StatesGroup


class IdeaStates(StatesGroup):
    WAITING_TITLE = State()
    WAITING_DESCRIPTION = State()
    WAITING_CATEGORY = State()
    WAITING_LOCATION = State()
    CONFIRM_SUBMIT = State()


class StartStates(StatesGroup):
    WAITING_PHONE = State()


class ModerationStates(StatesGroup):
    WAITING_REJECT_REASON = State()


class VoteStates(StatesGroup):
    WAITING_ID = State()


class StatusStates(StatesGroup):
    WAITING_ID = State()