"""
Загрузка дат поздравлений архиереев-викариев (наместников монастырей).

Источник — «даты поздравлений викарии.pdf», перенесённый в data/vicar_dates.csv:
сан, монашеское имя, день ангела (ДД.ММ), постриг и хиротонии (ДД.ММ.ГГГГ).

Архиерей ищется среди насельников по сану и монашескому имени, поэтому
сначала нужно загрузить списки монастырей (import_monasteries.py).
Повторный запуск безопасен — даты просто перезаписываются.

Использование:
    python3 import_vicar_dates.py
    python3 import_vicar_dates.py data/vicar_dates.csv
"""
import csv
import os
import sys

import config
import utils
from database import Database

DEFAULT_PATH = os.path.join("data", "vicar_dates.csv")
DATE_FIELDS = [
    "tonsure_date",
    "deacon_ordination_date",
    "priest_ordination_date",
    "bishop_ordination_date",
]


def main() -> None:
    file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PATH
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return

    db = Database()
    monks = db.get_all_priests(category=config.CATEGORY_MONK)

    print("=== ДАТЫ ВИКАРИЕВ ===")
    with open(file_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            status = utils.validate_status(row["status"]) or row["status"]
            name = row["monastic_name"].strip().lower()
            found = [p for p in monks if p.status == status and p.monastic_name.lower() == name]
            if len(found) != 1:
                print(f"❌ {status} {row['monastic_name']}: найдено записей — {len(found)} "
                      f"(загружены ли списки монастырей?)")
                continue

            person = found[0]
            person.name_day = row["name_day"].strip()
            for field_name in DATE_FIELDS:
                value = utils.parse_date(row[field_name])
                if row[field_name].strip() and not value:
                    print(f"⚠️  {person.short_title()}: не разобрана дата {field_name}={row[field_name]!r}")
                setattr(person, field_name, value)
            db.update_priest(person)
            print(f"✅ {person.short_title()}: день ангела {person.name_day}, "
                  f"постриг {utils.format_date(person.tonsure_date)}, "
                  f"диакон {utils.format_date(person.deacon_ordination_date)}, "
                  f"иерей {utils.format_date(person.priest_ordination_date)}, "
                  f"епископ {utils.format_date(person.bishop_ordination_date)}")


if __name__ == "__main__":
    main()
