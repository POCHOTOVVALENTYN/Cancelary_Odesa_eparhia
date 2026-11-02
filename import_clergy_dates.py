"""
Уточнение дат священнослужителей для «Именинников»: дата рождения, день
ангела, постриг, хиротонии в диакона и иерея (а также сан и послушание).

Источник — data/clergy_dates.csv. Человек ищется по фамилии и имени
(у монашествующих — ещё и по монашескому имени), во всех категориях.
Пустая ячейка значение в базе не трогает. Скрипт печатает, что изменилось.
Повторный запуск безопасен.

Использование:
    python3 import_clergy_dates.py
    python3 import_clergy_dates.py data/clergy_dates.csv
    python3 import_clergy_dates.py --dry-run
"""
import csv
import os
import sys

import utils
from database import Database

DEFAULT_PATH = os.path.join("data", "clergy_dates.csv")
DATE_FIELDS = [
    ("birth_date", "рождение"),
    ("tonsure_date", "постриг"),
    ("deacon_ordination_date", "диакон"),
    ("priest_ordination_date", "иерей"),
]


def main() -> None:
    args = [a for a in sys.argv[1:] if a != "--dry-run"]
    dry_run = "--dry-run" in sys.argv
    file_path = args[0] if args else DEFAULT_PATH
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    db = Database()
    everyone = db.get_all_priests()

    print("=== ДАТЫ СВЯЩЕННОСЛУЖИТЕЛЕЙ ===" + (" (проверка, без записи)" if dry_run else ""))
    with open(file_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            row = {k: (v or "").strip() for k, v in row.items()}
            who = f"{row['surname']} {row['name']}" + (f" ({row['monastic_name']})" if row["monastic_name"] else "")
            found = [
                p for p in everyone
                if p.surname.upper() == row["surname"].upper()
                and p.name.lower() == row["name"].lower()
                and (not row["monastic_name"] or (p.monastic_name or "").lower() == row["monastic_name"].lower())
            ]
            if len(found) != 1:
                print(f"❌ {who}: найдено записей — {len(found)}")
                continue

            person = found[0]
            changes = []

            if row["status"]:
                status = utils.validate_status(row["status"])
                if not status:
                    print(f"⚠️  {who}: неизвестный сан {row['status']!r}, сан не меняется")
                elif status != person.status:
                    changes.append(f"сан {person.status} → {status}")
                    person.status = status

            if row["name_day"] and row["name_day"] != person.name_day:
                changes.append(f"день ангела {person.name_day or '—'} → {row['name_day']}")
                person.name_day = row["name_day"]

            for field_name, label in DATE_FIELDS:
                if not row[field_name]:
                    continue
                value = utils.parse_date(row[field_name])
                if not value:
                    print(f"⚠️  {who}: не разобрана дата {field_name}={row[field_name]!r}")
                    continue
                old = getattr(person, field_name)
                if value != old:
                    changes.append(f"{label} {utils.format_date(old) if old else '—'} → {utils.format_date(value)}")
                    setattr(person, field_name, value)
            if person.birth_date:
                person.birth_year = person.birth_date.year

            # послушание дополняется, а не заменяется: в нём бывают награды из списка монастыря
            if row["obedience"] and row["obedience"].lower() not in (person.obedience or "").lower():
                new_obedience = "; ".join(x for x in [row["obedience"], person.obedience] if x)
                changes.append(f"послушание → {new_obedience}")
                person.obedience = new_obedience

            if not changes:
                print(f"✔️  {person.short_title()}: всё совпадает")
                continue
            if not dry_run:
                db.update_priest(person)
            print(f"✅ {person.short_title()}: " + "; ".join(changes))


if __name__ == "__main__":
    main()
