"""
Скрипт проверки: вывод дьяконов из базы данных.

Использование:
    python3 check_diakons.py
"""
from database import Database


def main() -> None:
    db = Database()
    all_priests = db.get_all_priests()

    diakons = [
        p for p in all_priests
        if p.status and ("диакон" in p.status.lower())
    ]

    print("=== ПРОВЕРКА ДЬЯКОНОВ ===")
    print(f"Всего найдено дьяконов: {len(diakons)}\n")

    for i, p in enumerate(diakons[:50], 1):
        fio = " ".join([x for x in [p.surname, p.name, p.patronymic] if x])
        print(f"{i}. {fio} | {p.status} | {p.service_place or 'место служения не указано'}")

    if len(diakons) > 50:
        print(f"\n... и ещё {len(diakons) - 50} дьяконов")


if __name__ == "__main__":
    main()

