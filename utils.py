"""
Вспомогательные функции
"""
from datetime import date, datetime, timedelta
from typing import Optional
import config


def parse_date(date_string: str) -> Optional[date]:
    """Парсинг даты из строки (форматы: DD.MM.YYYY, YYYY-MM-DD)"""
    if not date_string:
        return None

    date_string = date_string.strip()

    # Попытка парсинга формата DD.MM.YYYY
    try:
        return datetime.strptime(date_string, "%d.%m.%Y").date()
    except ValueError:
        pass

    # Попытка парсинга формата YYYY-MM-DD
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        pass

    return None


def format_date(d: Optional[date]) -> str:
    """Форматирование даты в строку DD.MM.YYYY"""
    if not d:
        return "Не указано"
    return d.strftime("%d.%m.%Y")


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in config.ADMIN_IDS


def validate_status(status: str) -> Optional[str]:
    """Валидация и нормализация статуса священника"""
    status_lower = status.lower().strip()

    for key, value in config.PRIEST_STATUSES.items():
        if key in status_lower:
            return value

    return None


def split_message(text: str, max_length: int = config.MAX_MESSAGE_LENGTH) -> list:
    """Разделение длинного сообщения на части"""
    if len(text) <= max_length:
        return [text]

    parts = []
    current_part = ""

    for line in text.split("\n"):
        if len(current_part) + len(line) + 1 > max_length:
            if current_part:
                parts.append(current_part)
                current_part = line
            else:
                # Если одна строка слишком длинная, разбиваем её
                while len(line) > max_length:
                    parts.append(line[:max_length])
                    line = line[max_length:]
                current_part = line
        else:
            current_part += "\n" + line if current_part else line

    if current_part:
        parts.append(current_part)

    return parts


# ==== Вспомогательные функции для возрастов и юбилеев ====

def calculate_age(birth_date: Optional[date], today: Optional[date] = None) -> Optional[int]:
    """Возвращает возраст в годах от даты рождения до today."""
    if not birth_date:
        return None
    today = today or date.today()
    years = today.year - birth_date.year
    if (today.month, today.day) < (birth_date.month, birth_date.day):
        years -= 1
    return years


def years_since(d: Optional[date], today: Optional[date] = None) -> Optional[int]:
    """Возвращает количество полных лет с даты d до today."""
    if not d:
        return None
    today = today or date.today()
    years = today.year - d.year
    if (today.month, today.day) < (d.month, d.day):
        years -= 1
    return years


def is_jubilee(years: Optional[int]) -> bool:
    """Проверяет, является ли количество лет юбилеем (кратным 5 и >= 5)."""
    return years is not None and years >= 5 and years % 5 == 0


def get_target_date(days_ahead: int, today: Optional[date] = None) -> date:
    """Возвращает дату today + days_ahead."""
    today = today or date.today()
    return today + timedelta(days=days_ahead)

