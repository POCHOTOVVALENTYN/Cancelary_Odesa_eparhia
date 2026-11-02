"""
Импорт списков насельников монастырей и привязка белого духовенства к монастырям.

Использование:
    python3 import_monasteries.py data/monasteries/            # все файлы папки
    python3 import_monasteries.py "33_СУ мм спис 25.docx" ...  # отдельные файлы
    python3 import_monasteries.py data/monasteries/ --dry-run  # только проверка, без записи

Поддерживаются .docx, .rtf и .doc. Файлы .rtf и старые .doc читаются
через macOS textutil, поэтому на сервере (Linux) их нужно заранее
пересохранить в Word как .docx — или запускать импорт на Mac и
копировать готовую базу.

Повторный запуск безопасен: уже загруженные люди (совпадение
ФИО + год рождения) обновляются, а не дублируются.
"""
import os
import sys

from database import Database
from monastery_importer import MonasteryImporter, link_white_clergy

SUPPORTED = (".docx", ".doc", ".rtf")


def collect_files(args):
    files = []
    for arg in args:
        if os.path.isdir(arg):
            for name in sorted(os.listdir(arg)):
                # ~$… — временные файлы Word
                if name.lower().endswith(SUPPORTED) and not name.startswith("~$"):
                    files.append(os.path.join(arg, name))
        elif os.path.exists(arg):
            files.append(arg)
        else:
            print(f"❌ Не найден: {arg}")
    return files


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv
    if not args:
        print(__doc__)
        return

    files = collect_files(args)
    if not files:
        print("❌ Нет файлов для импорта")
        return

    db = Database()
    importer = MonasteryImporter(db, dry_run=dry_run)

    print("=== ИМПОРТ СПИСКОВ МОНАСТЫРЕЙ" + (" (ПРОВЕРКА, БЕЗ ЗАПИСИ)" if dry_run else "") + " ===\n")
    total_added = total_updated = 0
    failed = []

    for path in files:
        result = importer.import_file(path)
        name = os.path.basename(path)
        if result.errors and not result.rows:
            print(f"❌ {name}: {result.errors[0]}")
            failed.append(name)
            continue

        kind = "мужской" if result.gender == "male" else "женский"
        print(f"✅ {name}")
        print(f"   {result.monastery} ({kind})")
        line = f"   Строк: {result.rows}, добавлено: {result.added}, обновлено: {result.updated}"
        if result.removed:
            line += f", выбыли из списка: {result.removed}"
        print(line)
        for msg in result.errors:
            print(f"   ⚠️  {msg}")
        for msg in result.warnings:
            print(f"   ℹ️  {msg}")
        total_added += result.added
        total_updated += result.updated

    print(f"\nИтого: добавлено {total_added}, обновлено {total_updated}")
    if failed:
        print(f"Не загружены ({len(failed)}): " + "; ".join(failed))

    print("\n=== ДУХОВЕНСТВО, СЛУЖАЩЕЕ ПРИ МОНАСТЫРЯХ ===")
    if dry_run:
        print("(при --dry-run монастыри не создаются, привязка по уже существующим монастырям)")
    report = link_white_clergy(db, dry_run=dry_run)
    for priest, monastery in report["linked"]:
        print(f"🔗 {priest.surname} {priest.name} ({priest.status}) → {monastery}")
    for priest in report["ambiguous"]:
        print(f"❓ Несколько монастырей подходят: {priest.surname} {priest.name} (id {priest.id}): "
              f"{' '.join(priest.service_place.split())}")
    for priest in report["unmatched"]:
        print(f"➖ Монастырь не найден среди загруженных: {priest.surname} {priest.name} (id {priest.id}): "
              f"{' '.join(priest.service_place.split())}")
    print(f"Привязано: {len(report['linked'])}")


if __name__ == "__main__":
    main()
