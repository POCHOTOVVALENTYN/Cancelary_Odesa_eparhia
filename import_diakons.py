"""
Отдельный скрипт для импорта списка дьяконов из файла diakons.xlsx.

Использование:
    python3 import_diakons.py
    python3 import_diakons.py data/diakons.xlsx

Ожидаемый файл по умолчанию:
    ./data/diakons.xlsx
"""
import os
import sys

from legacy_excel_importer import LegacyExcelImporter


DEFAULT_PATH = os.path.join("data", "diakons.xlsx")


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        print("Поместите diakons.xlsx в папку data и попробуйте снова.")
        print("Пример: python3 import_diakons.py data/diakons.xlsx")
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

