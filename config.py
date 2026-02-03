"""
Конфигурационный файл для Telegram-бота Одесской Епархии
"""
import os
from typing import List

# Токен бота (получить у @BotFather в Telegram)
BOT_TOKEN = os.getenv("BOT_TOKEN", "8246197972:AAEA4TCP8NpmLvX3nCJnXdpSkjXPqDo_EeQ")

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
