"""
Парсер для файла kliriki.xlsx (извлечение ФИО и телефонов).

Структура:
- Колонка D: Положение (Настоятель), сан, имя, отчество, фамилия
  (фамилия иногда переносится на новую строку)
- Колонка E: номера телефонов
"""

import re
from typing import Optional, Tuple
import pandas as pd


class KlirikiParser:
    """Парсер для извлечения ФИО и телефонов из kliriki.xlsx."""

    # Известные саны для удаления из текста
    KNOWN_RANKS = [
        "настоятель",
        "протоиерей",
        "иерей",
        "священник",
        "свящ",
        "прот",
        "диакон",
        "дьякон",
        "протодиакон",
        "протодьякон",
        "диак",
        "дьяк",
        "протод",
    ]

    def __init__(self, file_path: str):
        self.file_path = file_path
        # Читаем Excel с помощью pandas
        self.df = pd.read_excel(file_path, engine='openpyxl', header=None)

    def _clean_lines(self, cell_value) -> list:
        """Разбивает значение ячейки по строкам и очищает."""
        if cell_value is None:
            return []
        s = str(cell_value).replace("\r", "\n")
        lines = []
        for raw in s.split("\n"):
            line = raw.strip()
            if line and not self._should_skip(line):
                lines.append(line)
        return lines

    def _should_skip(self, line: str) -> bool:
        """Проверяет, нужно ли пропустить строку."""
        line_lower = line.lower()
        # Пропускаем "обслуживается клириками"
        if "обслуживается" in line_lower or "клириками" in line_lower:
            return True
        return False

    def _remove_ranks(self, text: str) -> str:
        """Удаляет саны и должности из текста."""
        text_clean = text
        for rank in self.KNOWN_RANKS:
            # Удаляем сан как отдельное слово (с точкой или без)
            text_clean = re.sub(
                rf"\b{re.escape(rank)}\.?\b",
                "",
                text_clean,
                flags=re.IGNORECASE,
            )
        # Убираем лишние пробелы
        text_clean = " ".join(text_clean.split())
        return text_clean.strip()

    def parse_fio_from_column_d(self, cell_value) -> Tuple[str, str, str]:
        """
        Извлекает ФИО из колонки D.
        
        Возвращает (name, patronymic, surname).
        """
        lines = self._clean_lines(cell_value)
        if not lines:
            return "", "", ""

        # Объединяем все строки (фамилия может быть на следующей строке)
        full_text = " ".join(lines)
        
        # Убираем саны и должности
        clean_text = self._remove_ranks(full_text)
        
        # Разбиваем на слова
        words = [w for w in clean_text.split() if w and len(w) > 1]
        
        if len(words) >= 3:
            # Формат: Имя Отчество Фамилия (обычно)
            name = words[0]
            patronymic = words[1]
            surname = " ".join(words[2:])  # Фамилия может быть из нескольких слов
        elif len(words) == 2:
            name, surname = words
            patronymic = ""
        elif len(words) == 1:
            surname = words[0]
            name = ""
            patronymic = ""
        else:
            return "", "", ""
        
        return name, patronymic, surname

    def parse_phone_from_column_e(self, cell_value) -> str:
        """Извлекает номер телефона из колонки E."""
        if cell_value is None:
            return ""
        
        phone = str(cell_value).strip()
        
        # Убираем пробелы, тире
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        
        # Если это число (Excel может привести к числу)
        if phone.replace("+", "").replace(".", "").isdigit():
            # Убираем десятичную точку, если есть
            phone = phone.split(".")[0]
            return phone
        
        return phone

    def extract_all_entries(self) -> list:
        """
        Извлекает все записи (ФИО + телефон) из файла.
        
        Возвращает список словарей:
        [
            {"row": 1, "name": "...", "patronymic": "...", "surname": "...", "phone": "..."},
            ...
        ]
        """
        entries = []
        
        # Проходим по всем строкам DataFrame
        for idx, row in self.df.iterrows():
            # Колонка D - это индекс 3 (0-based)
            # Колонка E - это индекс 4
            col_d = row[3] if len(row) > 3 else None
            col_e = row[4] if len(row) > 4 else None
            
            # Пропускаем пустые строки
            if pd.isna(col_d) and pd.isna(col_e):
                continue
            
            name, patronymic, surname = self.parse_fio_from_column_d(col_d)
            phone = self.parse_phone_from_column_e(col_e)
            
            # Если есть хотя бы фамилия или имя
            if surname or name:
                entries.append({
                    "row": idx + 1,  # 1-based row number
                    "name": name,
                    "patronymic": patronymic,
                    "surname": surname,
                    "phone": phone,
                })
        
        return entries
