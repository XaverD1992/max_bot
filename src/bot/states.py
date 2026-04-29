"""Состояния для пошагового диалога подачи инициативы"""
from enum import Enum

class IdeaStates(Enum):
    WAITING_TITLE = "waiting_title"
    WAITING_DESCRIPTION = "waiting_description"
    WAITING_CATEGORY = "waiting_category"
    WAITING_LOCATION = "waiting_location"
    CONFIRM_SUBMIT = "confirm_submit"