#!/usr/bin/env python3
"""
Скрипт для импорта номеров телефонов из kliriki.xlsx в базу данных.

Сопоставляет записи по ФИО (имя + отчество + фамилия) и обновляет поле phone.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent))

from kliriki_parser import KlirikiParser
from database import Database
from models import Priest


def normalize_fio(name: str, patronymic: str, surname: str) -> str:
    """Нормализует ФИО для сопоставления (убирает пробелы, приводит к нижнему регистру)."""
    parts = []
    if surname:
        parts.append(surname.strip().lower())
    if name:
        parts.append(name.strip().lower())
    if patronymic:
        parts.append(patronymic.strip().lower())
    return " ".join(parts)


def find_matching_priest(
    kliriki_entry: dict,
    all_priests: List[Priest]
) -> Optional[Priest]:
    """
    Находит священника/диакона в базе по ФИО из kliriki.xlsx.
    
    Сопоставление по нормализованному ФИО (фамилия + имя + отчество).
    """
    kliriki_fio = normalize_fio(
        kliriki_entry["name"],
        kliriki_entry["patronymic"],
        kliriki_entry["surname"]
    )
    
    if not kliriki_fio:
        return None
    
    for priest in all_priests:
        priest_fio = normalize_fio(priest.name, priest.patronymic, priest.surname)
        
        # Точное совпадение
        if priest_fio == kliriki_fio:
            return priest
        
        # Частичное совпадение (если фамилия и имя совпадают)
        kliriki_parts = kliriki_fio.split()
        priest_parts = priest_fio.split()
        
        if len(kliriki_parts) >= 2 and len(priest_parts) >= 2:
            # Сравниваем фамилию и имя
            if kliriki_parts[0] == priest_parts[0] and kliriki_parts[1] == priest_parts[1]:
                return priest
    
    return None


def main():
    """Основная функция импорта телефонов."""
    # Путь к файлу kliriki.xlsx
    kliriki_path = Path(__file__).parent / "data" / "kliriki.xlsx"
    
    if not kliriki_path.exists():
        print(f"❌ Файл {kliriki_path} не найден!")
        print("Убедитесь, что файл kliriki.xlsx находится в папке data/")
        return
    
    print(f"📂 Загрузка файла: {kliriki_path}")
    
    # Инициализация парсера
    try:
        parser = KlirikiParser(str(kliriki_path))
        entries = parser.extract_all_entries()
        print(f"✅ Извлечено записей из kliriki.xlsx: {len(entries)}")
    except Exception as e:
        print(f"❌ Ошибка при парсинге файла: {e}")
        return
    
    # Инициализация базы данных
    db = Database()
    all_priests = db.get_all_priests()
    print(f"✅ Загружено священников/диаконов из БД: {len(all_priests)}")
    
    # Сопоставление и обновление
    matched_count = 0
    updated_count = 0
    not_matched = []
    
    for entry in entries:
        # Ищем совпадение
        priest = find_matching_priest(entry, all_priests)
        
        if priest:
            matched_count += 1
            
            # Обновляем телефон, если он есть
            if entry["phone"]:
                priest.phone = entry["phone"]
                if db.update_priest(priest):
                    updated_count += 1
                    print(
                        f"✅ Обновлен телефон для: {priest.surname} {priest.name} {priest.patronymic} "
                        f"-> {entry['phone']}"
                    )
                else:
                    print(
                        f"⚠️  Не удалось обновить: {priest.surname} {priest.name} {priest.patronymic}"
                    )
        else:
            not_matched.append(entry)
    
    # Итоговая статистика
    print("\n" + "="*60)
    print("📊 СТАТИСТИКА ИМПОРТА")
    print("="*60)
    print(f"Всего записей в kliriki.xlsx: {len(entries)}")
    print(f"Найдено совпадений с БД: {matched_count}")
    print(f"Обновлено телефонов: {updated_count}")
    print(f"Не найдено совпадений: {len(not_matched)}")
    
    if not_matched:
        print("\n⚠️  Записи без совпадений:")
        for entry in not_matched[:20]:  # Показываем первые 20
            print(
                f"  - Строка {entry['row']}: {entry['surname']} {entry['name']} "
                f"{entry['patronymic']} (тел: {entry['phone']})"
            )
        if len(not_matched) > 20:
            print(f"  ... и еще {len(not_matched) - 20} записей")
    
    print("="*60)
    print("✅ Импорт завершен!")


if __name__ == "__main__":
    main()
