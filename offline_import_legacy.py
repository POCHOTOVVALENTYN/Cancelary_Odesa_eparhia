"""
Офлайн-скрипт для импорта и анализа данных из файла формата A–K

Запускать ИЗ КОРНЯ проекта:

    cd /Users/valentin/Cancellary_Bot
    source venv/bin/activate
    python3 offline_import_legacy.py

По умолчанию ожидается файл:
    data/priests_odess.xlsx
"""

import os
from collections import Counter

from legacy_excel_importer import LegacyExcelImporter
from database import Database


DATA_DIR = "data"
DEFAULT_FILENAME = "priests_odess.xlsx"


def run_import(file_path: str) -> None:
    """Выполняет импорт из указанного файла и печатает статистику."""
    print("=== ОФЛАЙН-ИМПОРТ ДАННЫХ (формат A–K) ===")
    print(f"Файл: {os.path.abspath(file_path)}")

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
        print("\nПервые ошибки:")
        print(importer.get_error_report())


def analyze_database() -> None:
    """Печатает сводную информацию по текущей базе данных."""
    print("\n=== АНАЛИЗ ТЕКУЩЕЙ БАЗЫ ДАННЫХ ===")
    db = Database()

    total = db.get_total_count()
    print(f"Всего записей в таблице priests: {total}")

    # Распределение по статусам
    print("\n--- РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ ---")
    statuses_counter: Counter[str] = Counter()
    all_priests = db.get_all_priests()
    for p in all_priests:
        statuses_counter[p.status or "Не указан"] += 1

    for status, count in statuses_counter.most_common():
        print(f"{status}: {count}")

    # Сколько без даты рождения / без места служения
    no_birth_date = sum(1 for p in all_priests if p.birth_date is None)
    no_service_place = sum(1 for p in all_priests if not p.service_place)

    print("\n--- КАЧЕСТВО ДАННЫХ ---")
    print(f"Без даты рождения: {no_birth_date}")
    print(f"Без места служения: {no_service_place}")

    # Показать несколько примеров
    print("\n--- ПРИМЕРЫ ЗАПИСЕЙ (первые 5) ---")
    for p in all_priests[:5]:
        fio = " ".join(
            x
            for x in [p.surname, p.name, p.patronymic]
            if x
        )
        print(
            f"- {fio} | Статус: {p.status} | Рождение: "
            f"{p.birth_date.strftime('%d.%m.%Y') if p.birth_date else 'нет данных'} | "
            f"Место служения: {p.service_place or 'нет данных'}"
        )


def main() -> None:
    # Подготовка пути к файлу
    if not os.path.isdir(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)

    file_path = os.path.join(DATA_DIR, DEFAULT_FILENAME)

    # 1. Импорт из файла
    run_import(file_path)

    # 2. Анализ текущего состояния базы
    analyze_database()


if __name__ == "__main__":
    main()

"""
Офлайн-скрипт для импорта данных из Excel-файла формата A–K
и проверки результатов в базе данных.

Ожидаемый путь к файлу по умолчанию: ./data/priests_odess.xlsx
"""

import os
from typing import Optional

from legacy_excel_importer import LegacyExcelImporter
from database import Database


DEFAULT_PATH = os.path.join("data", "priests_odess.xlsx")


def run_import(file_path: str) -> None:
    """Запуск импорта и вывод статистики."""
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    print(f"📥 Импорт из файла: {file_path}")
    importer = LegacyExcelImporter()
    result = importer.import_from_file(file_path)

    print("\n=== РЕЗУЛЬТАТ ИМПОРТА ===")
    print(f"Всего строк в файле: {result['total']}")
    print(f"Успешно импортировано записей: {result['success']}")
    print(f"Ошибок: {result['errors']}")

    if result["errors"] > 0:
        print("\nПервые ошибки (максимум 20):")
        print(importer.get_error_report())


def verify_database(limit: int = 10) -> None:
    """Проверка содержимого базы данных после импорта."""
    db = Database()
    total = db.get_total_count()

    print("\n=== ПРОВЕРКА БАЗЫ ДАННЫХ ===")
    print(f"Всего записей в таблице priests: {total}")

    priests = db.get_all_priests(limit=limit, offset=0)
    if not priests:
        print("Таблица пуста.")
        return

    print(f"\nПервые {len(priests)} записей:")
    for i, p in enumerate(priests, 1):
        fio = " ".join(
            [x for x in [p.surname, p.name, p.patronymic] if x]
        )
        print(f"{i}. {fio} | {p.status} | {p.service_place}")


def main(path: Optional[str] = None) -> None:
    file_path = path or DEFAULT_PATH
    run_import(file_path)
    verify_database()


if __name__ == "__main__":
    # Можно переопределить путь через переменную окружения OFFLINE_IMPORT_PATH
    override_path = os.getenv("OFFLINE_IMPORT_PATH")
    main(override_path)

