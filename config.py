"""
Конфигурационный файл для Telegram-бота Одесской Епархии
"""
import os
from typing import List

# Токен бота (получить у @BotFather в Telegram).
# Берётся только из переменной окружения BOT_TOKEN — в репозитории токен не хранится.
# Локально: файл .env (см. .env.example) подхватывает start.sh,
# на сервере: EnvironmentFile=/home/opc/telegram-bot/.env в systemd-юните.
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()


def require_bot_token() -> str:
    """Вернуть токен бота или упасть с понятной ошибкой, если он не задан"""
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задана переменная окружения BOT_TOKEN. "
            "Задайте её (export BOT_TOKEN='токен' или файл .env, см. .env.example) "
            "и перезапустите бота."
        )
    return BOT_TOKEN

# ID администраторов (список ID пользователей Telegram)
ADMIN_IDS: List[int] = [
    830196453,
    534966512,
    751473735,
]

# Настройки базы данных
DATABASE_PATH = "database.db"

# Настройки бота
MAX_MESSAGE_LENGTH = 4096  # Максимальная длина сообщения Telegram
ITEMS_PER_PAGE = 10  # Количество элементов на странице

# Статусы священников
PRIEST_STATUSES = {
    "протоиерей": "Протоиерей",
    "иерей": "Иерей",
    "диакон": "Диакон",
    "протодиакон": "Протодиакон"
}
