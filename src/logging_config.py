import logging
import sys
from src.config import settings

def setup_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Настройка кодировки для stdout
    sys.stdout.reconfigure(encoding='utf-8')

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("bot.log", encoding="utf-8", mode="a")
        ]
    )
    
    # Подавляем шумные логи библиотек
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    
    logger = logging.getLogger("tos_mvp")
    logger.info(f"Логирование настроено. Уровень: {settings.LOG_LEVEL}")
    return logger

logger = setup_logging()