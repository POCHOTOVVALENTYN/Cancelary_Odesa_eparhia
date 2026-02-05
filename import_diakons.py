"""
Отдельный скрипт для импорта списка дьяконов из файла diakons.xlsx.

Использование:
    python3 import_diakons.py

Ожидаемый файл:
    ./diakons.xlsx
"""
import os

from legacy_excel_importer import LegacyExcelImporter


DEFAULT_PATH = "diakons.xlsx"


def main() -> None:
    file_path = DEFAULT_PATH
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        print("Поместите diakons.xlsx в корень проекта и попробуйте снова.")
        return

    importer = LegacyExcelImporter()
    result = importer.import_from_file(file_path)

    print("=== ИМПОРТ ДЬЯКОНОВ ===")
    print(f"Файл: {file_path}")
    print(f"Всего строк: {result['total']}")
    print(f"Успешно добавлено: {result['success']}")
    print(f"Ошибок: {result['errors']}")

    if result["errors"] > 0:
        print("\nПервые ошибки:")
        print(importer.get_error_report())


if __name__ == "__main__":
    main()

