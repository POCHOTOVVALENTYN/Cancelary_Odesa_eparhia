#!/usr/bin/env python3
"""
Тестовый скрипт для проверки чтения kliriki.xlsx
"""

import sys
from pathlib import Path

print("Тест 1: Проверка наличия файла...")
kliriki_path = Path("data/kliriki.xlsx")
if kliriki_path.exists():
    print(f"✅ Файл найден: {kliriki_path}")
    print(f"   Размер: {kliriki_path.stat().st_size} байт")
else:
    print(f"❌ Файл не найден: {kliriki_path}")
    sys.exit(1)

print("\nТест 2: Импорт pandas...")
try:
    import pandas as pd
    print("✅ pandas импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта pandas: {e}")
    sys.exit(1)

print("\nТест 3: Импорт openpyxl...")
try:
    import openpyxl
    print("✅ openpyxl импортирован")
except ImportError as e:
    print(f"❌ Ошибка импорта openpyxl: {e}")
    sys.exit(1)

print("\nТест 4: Чтение файла с pandas...")
try:
    df = pd.read_excel(kliriki_path, engine='openpyxl', header=None)
    print(f"✅ Файл прочитан!")
    print(f"   Строк: {len(df)}")
    print(f"   Столбцов: {len(df.columns)}")
    print("\nПервые 3 строки колонки D (индекс 3):")
    for idx in range(min(3, len(df))):
        print(f"   Строка {idx+1}: {df.iloc[idx, 3] if len(df.columns) > 3 else 'N/A'}")
except Exception as e:
    print(f"❌ Ошибка чтения: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Все тесты пройдены!")
