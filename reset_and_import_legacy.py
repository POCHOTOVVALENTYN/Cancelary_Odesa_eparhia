"""
Скрипт для ПОЛНОЙ переинициализации данных о священниках
и повторного импорта из файла формата A–K.

Важно: этот скрипт УДАЛЯЕТ все записи из таблицы priests,
а затем импортирует данные заново.

Запускать ИЗ КОРНЯ проекта:

    cd /Users/valentin/Cancellary_Bot
    source venv/bin/activate
    python3 reset_and_import_legacy.py

Ожидаемый файл по умолчанию:

    ./data/priests_odess.xlsx

Структура файла (колонки A–K):
- A: порядковый номер (игнорируется)
- B: Фамилия Имя Отчество (одной строкой)
- C: сан: "свящ." → Иерей, "прот." → Протоиерей
- D: национальность: "укр.", "рус.", "молд." и т.п.
- E: год рождения и день тезоименитства (1 или 2 даты в ячейке)
- F: даты рукоположения в диакона и священника (1 или 2 даты/года)
- G: место рождения
- H: духовное образование
- I: светское образование
- J: место служения
- K: текущая награда
"""

import os
from collections import Counter

from database import Database
from legacy_excel_importer import LegacyExcelImporter

DEFAULT_PATH = os.path.join("data", "priests_odess.xlsx")


def reset_priests_table() -> None:
    """Полностью очищает таблицу priests."""
    print("=== СБРОС ТАБЛИЦЫ PRIESTS ===")
    db = Database()
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM priests")
    conn.commit()
    conn.close()
    print("✅ Все записи из таблицы priests удалены.\n")


def import_from_excel(file_path: str) -> None:
    """Импортирует данные из Excel и выводит статистику."""
    print("=== ИМПОРТ ИЗ EXCEL (формат A–K) ===")
    print(f"Путь к файлу: {os.path.abspath(file_path)}")

    if not os.path.exists(file_path):
        print("❌ Файл не найден. Убедитесь, что он существует по указанному пути.")
        return

    importer = LegacyExcelImporter()
    result = importer.import_from_file(file_path)

    print("\n--- РЕЗУЛЬТАТ ИМПОРТА ---")
    print(f"Всего строк в файле: {result['total']}")
    print(f"Успешно импортировано: {result['success']}")
    print(f"Ошибок: {result['errors']}")

    if result["errors"] > 0:
        print("\nПервые ошибки (максимум 20):")
        print(importer.get_error_report())


def analyze_database() -> None:
    """Печатает детализированный отчёт по данным в базе."""
    print("\n=== АНАЛИЗ БАЗЫ ДАННЫХ ===")
    db = Database()

    total = db.get_total_count()
    print(f"Всего записей в таблице priests: {total}")

    priests = db.get_all_priests()
    if not priests:
        print("Таблица пуста.")
        return

    # Распределение по статусам
    print("\n--- РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ ---")
    status_counter: Counter[str] = Counter()
    for p in priests:
        status_counter[p.status or "Не указан"] += 1

    for status, count in status_counter.most_common():
        print(f"{status}: {count}")

    # Распределение по национальностям
    print("\n--- РАСПРЕДЕЛЕНИЕ ПО НАЦИОНАЛЬНОСТЯМ ---")
    nat_counter: Counter[str] = Counter()
    for p in priests:
        nat_counter[p.nationality or "Не указана"] += 1
    for nat, count in nat_counter.most_common():
        print(f"{nat}: {count}")

    # Качество данных
    no_birth_date = sum(1 for p in priests if p.birth_date is None)
    no_service_place = sum(1 for p in priests if not p.service_place)
    no_spiritual_edu = sum(1 for p in priests if not p.education)
    no_secular_edu = sum(1 for p in priests if not p.secular_education)

    print("\n--- КАЧЕСТВО ДАННЫХ ---")
    print(f"Без даты рождения: {no_birth_date}")
    print(f"Без места служения: {no_service_place}")
    print(f"Без духовного образования: {no_spiritual_edu}")
    print(f"Без светского образования: {no_secular_edu}")

    # Примеры записей
    print("\n--- ПРИМЕРЫ ЗАПИСЕЙ (первые 10) ---")
    for i, p in enumerate(priests[:10], start=1):
        fio = " ".join(
            part for part in [p.surname, p.name, p.patronymic] if part
        )
        birth = p.birth_date.strftime("%d.%m.%Y") if p.birth_date else "нет данных"
        deacon = (
            p.deacon_ordination_date.strftime("%d.%m.%Y")
            if p.deacon_ordination_date
            else "нет"
        )
        priest_date = (
            p.priest_ordination_date.strftime("%d.%m.%Y")
            if p.priest_ordination_date
            else "нет"
        )
        print(
            f"{i}. {fio} | Сан: {p.status} | Нац.: {p.nationality or 'н/д'} | "
            f"Рождение: {birth} | Именины: {p.name_day or 'н/д'} | "
            f"Диакон: {deacon} | Священник: {priest_date} | "
            f"Служение: {p.service_place or 'н/д'}"
        )


def main() -> None:
    file_path = DEFAULT_PATH

    # 1. Сброс существующих данных
    reset_priests_table()

    # 2. Импорт из Excel
    import_from_excel(file_path)

    # 3. Анализ результата
    analyze_database()


if __name__ == "__main__":
    main()

