"""
Модуль для работы с базой данных
"""
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
from models import Priest
import config


# Названия всех монастырей человека (наместник может числиться в нескольких)
_MONASTERY_NAMES = """
    COALESCE(
        (SELECT group_concat(m2.name, '; ')
         FROM monastery_members mm2 JOIN monasteries m2 ON m2.id = mm2.monastery_id
         WHERE mm2.priest_id = p.id),
        m.name
    )
"""

# Выборка священника вместе с названием монастыря
_SELECT_PRIESTS = f"""
    SELECT p.*, {_MONASTERY_NAMES} AS monastery_name
    FROM priests p
    LEFT JOIN monasteries m ON m.id = p.monastery_id
"""

# Поля, которые записываются при добавлении/обновлении (порядок важен)
_WRITE_FIELDS = [
    "name",
    "patronymic",
    "surname",
    "birth_date",
    "birth_place",
    "nationality",
    "status",
    "name_day",
    "deacon_ordination_date",
    "priest_ordination_date",
    "ordination_date",
    "service_place",
    "education",
    "secular_education",
    "last_reward",
    "phone",
    "category",
    "monastery_id",
    "monastic_name",
    "obedience",
    "birth_year",
    "ordination_years",
    "tonsure_date",
    "bishop_ordination_date",
]


class Database:
    """Класс для работы с базой данных SQLite"""

    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.init_database()

    def get_connection(self) -> sqlite3.Connection:
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_path)
        # Регистрируем функцию нижнего регистра для поиска на кириллице (SQLite LOWER не умеет в Unicode)
        conn.create_function("py_lower", 1, lambda s: s.lower() if isinstance(s, str) else s)
        conn.row_factory = sqlite3.Row
        return conn

    def init_database(self):
        """Инициализация базы данных и создание таблиц"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Базовое создание таблицы (при первом запуске)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS priests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                patronymic TEXT,
                surname TEXT NOT NULL,
                birth_date DATE,
                birth_place TEXT,
                nationality TEXT,
                status TEXT NOT NULL,
                name_day TEXT,
                deacon_ordination_date DATE,
                priest_ordination_date DATE,
                ordination_date DATE,
                service_place TEXT,
                education TEXT,
                secular_education TEXT,
                last_reward TEXT,
                phone TEXT,
                category TEXT NOT NULL DEFAULT 'white_clergy',
                monastery_id INTEGER REFERENCES monasteries(id),
                monastic_name TEXT,
                obedience TEXT,
                birth_year INTEGER,
                ordination_years TEXT,
                tonsure_date DATE,
                bishop_ordination_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monasteries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                gender TEXT NOT NULL CHECK (gender IN ('male', 'female')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Миграции для уже существующих баз данных (добавление недостающих колонок)
        cursor.execute("PRAGMA table_info(priests)")
        existing_columns = {row["name"] for row in cursor.fetchall()}

        migrations = [
            ("patronymic", "TEXT"),
            ("nationality", "TEXT"),
            ("name_day", "TEXT"),
            ("deacon_ordination_date", "DATE"),
            ("priest_ordination_date", "DATE"),
            ("secular_education", "TEXT"),
            ("phone", "TEXT"),
            ("category", "TEXT NOT NULL DEFAULT 'white_clergy'"),
            ("monastery_id", "INTEGER REFERENCES monasteries(id)"),
            ("monastic_name", "TEXT"),
            ("obedience", "TEXT"),
            ("birth_year", "INTEGER"),
            ("ordination_years", "TEXT"),
            ("tonsure_date", "DATE"),
            ("bishop_ordination_date", "DATE"),
        ]

        for column_name, column_type in migrations:
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE priests ADD COLUMN {column_name} {column_type}"
                )

        # Принадлежность к монастырям: один человек может числиться в нескольких
        # (например, архиерей — наместник двух обителей). priests.monastery_id — основной.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monastery_members (
                priest_id INTEGER NOT NULL REFERENCES priests(id) ON DELETE CASCADE,
                monastery_id INTEGER NOT NULL REFERENCES monasteries(id),
                PRIMARY KEY (priest_id, monastery_id)
            )
        """)
        # Перенос старых привязок: только для тех, у кого ещё нет ни одной записи о принадлежности
        cursor.execute("""
            INSERT OR IGNORE INTO monastery_members (priest_id, monastery_id)
            SELECT id, monastery_id FROM priests
            WHERE monastery_id IS NOT NULL
              AND id NOT IN (SELECT priest_id FROM monastery_members)
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priests_category ON priests(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_priests_monastery ON priests(monastery_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_members_monastery ON monastery_members(monastery_id)")

        conn.commit()
        conn.close()

    @staticmethod
    def _write_values(priest: Priest) -> list:
        """Значения полей в порядке _WRITE_FIELDS"""
        def iso(d: Optional[date]) -> Optional[str]:
            return d.isoformat() if d else None

        return [
            priest.name,
            priest.patronymic,
            priest.surname,
            iso(priest.birth_date),
            priest.birth_place,
            priest.nationality,
            priest.status,
            priest.name_day,
            iso(priest.deacon_ordination_date),
            iso(priest.priest_ordination_date),
            iso(priest.ordination_date),
            priest.service_place,
            priest.education,
            priest.secular_education,
            priest.last_reward,
            priest.phone,
            priest.category or config.CATEGORY_WHITE_CLERGY,
            priest.monastery_id,
            priest.monastic_name,
            priest.obedience,
            priest.birth_year,
            priest.ordination_years,
            iso(priest.tonsure_date),
            iso(priest.bishop_ordination_date),
        ]

    def add_priest(self, priest: Priest) -> int:
        """Добавление нового священника"""
        conn = self.get_connection()
        cursor = conn.cursor()

        placeholders = ", ".join("?" for _ in _WRITE_FIELDS)
        cursor.execute(
            f"INSERT INTO priests ({', '.join(_WRITE_FIELDS)}) VALUES ({placeholders})",
            self._write_values(priest),
        )

        priest_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return priest_id

    def get_priest_by_id(self, priest_id: int) -> Optional[Priest]:
        """Получение священника по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(f"{_SELECT_PRIESTS} WHERE p.id = ?", (priest_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_priest(row)
        return None

    def search_priests(self, query: str) -> List[Priest]:
        """Поиск по имени, фамилии, полному ФИО или монашескому имени"""
        conn = self.get_connection()
        cursor = conn.cursor()

        search_term = f"%{query.lower().strip()}%"
        cursor.execute(f"""
            {_SELECT_PRIESTS}
            WHERE py_lower(p.name) LIKE ?
               OR py_lower(p.surname) LIKE ?
               OR py_lower(p.surname || ' ' || p.name || ' ' || COALESCE(p.patronymic, '')) LIKE ?
               OR py_lower(COALESCE(p.monastic_name, '')) LIKE ?
               OR py_lower(p.status || ' ' || COALESCE(p.monastic_name, '')) LIKE ?
            ORDER BY p.surname, p.name
        """, (search_term,) * 5)

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_priest(row) for row in rows]

    def get_all_priests(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        category: Optional[str] = None,
    ) -> List[Priest]:
        """Получение всех записей с пагинацией (опционально — только одной категории)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        where = "WHERE p.category = ?" if category else ""
        params: list = [category] if category else []
        sql = f"{_SELECT_PRIESTS} {where} ORDER BY p.surname, p.name"
        if limit:
            sql += " LIMIT ? OFFSET ?"
            params += [limit, offset]
        cursor.execute(sql, params)

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_priest(row) for row in rows]

    def get_priests_by_status(self, status: str) -> List[Priest]:
        """Получение священников по статусу"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute(f"""
            {_SELECT_PRIESTS}
            WHERE py_lower(p.status) = py_lower(?)
            ORDER BY p.surname, p.name
        """, (status,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_priest(row) for row in rows]

    def update_priest(self, priest: Priest) -> bool:
        """Обновление информации о священнике"""
        if not priest.id:
            return False

        conn = self.get_connection()
        cursor = conn.cursor()

        assignments = ", ".join(f"{field} = ?" for field in _WRITE_FIELDS)
        cursor.execute(
            f"UPDATE priests SET {assignments}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            self._write_values(priest) + [priest.id],
        )

        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def delete_priest(self, priest_id: int) -> bool:
        """Удаление священника"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM monastery_members WHERE priest_id = ?", (priest_id,))
        cursor.execute("DELETE FROM priests WHERE id = ?", (priest_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

    def get_total_count(self, category: Optional[str] = None) -> int:
        """Получение общего количества записей (опционально — одной категории)"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if category:
            cursor.execute("SELECT COUNT(*) as count FROM priests WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT COUNT(*) as count FROM priests")
        count = cursor.fetchone()["count"]
        conn.close()

        return count

    # ===== Монастыри =====

    def get_or_create_monastery(self, name: str, gender: str) -> int:
        """Возвращает id монастыря по названию, создавая его при необходимости"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM monasteries WHERE name = ?", (name,))
        row = cursor.fetchone()
        if row:
            monastery_id = row["id"]
        else:
            cursor.execute(
                "INSERT INTO monasteries (name, gender) VALUES (?, ?)",
                (name, gender),
            )
            monastery_id = cursor.lastrowid
            conn.commit()
        conn.close()
        return monastery_id

    def get_monasteries(self) -> List[Dict]:
        """Все монастыри: [{'id', 'name', 'gender'}, ...]"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, gender FROM monasteries ORDER BY name")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_monastery(self, monastery_id: int) -> Optional[Dict]:
        """Монастырь по id: {'id', 'name', 'gender'}"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, gender FROM monasteries WHERE id = ?", (monastery_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_monasteries_with_counts(self, category: str, gender: Optional[str] = None) -> List[Dict]:
        """
        Монастыри с количеством записей указанной категории.

        Возвращает только монастыри, где есть хотя бы одна такая запись:
        [{'id', 'name', 'gender', 'count'}, ...]
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        sql = """
            SELECT m.id, m.name, m.gender, COUNT(p.id) AS count
            FROM monasteries m
            JOIN monastery_members mm ON mm.monastery_id = m.id
            JOIN priests p ON p.id = mm.priest_id AND p.category = ?
        """
        params: list = [category]
        if gender:
            sql += " WHERE m.gender = ?"
            params.append(gender)
        sql += " GROUP BY m.id ORDER BY m.name"
        cursor.execute(sql, params)

        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def get_monastery_people(
        self,
        category: str,
        monastery_id: Optional[int] = None,
    ) -> List[Tuple[str, Priest]]:
        """
        Записи категории, числящиеся в монастыре: [(название монастыря, запись), ...].

        Если monastery_id не указан — по всем монастырям (наместник нескольких
        обителей встречается под каждой из них).
        Порядок: монастырь, затем сан в порядке иерархии (как в исходных списках), затем фамилия.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        rank_order = list(config.MONASTIC_STATUSES.values()) + list(config.PRIEST_STATUSES.values())
        order_case = "CASE p.status " + " ".join(
            f"WHEN ? THEN {i}" for i in range(len(rank_order))
        ) + f" ELSE {len(rank_order)} END"

        sql = f"""
            SELECT p.*, {_MONASTERY_NAMES} AS monastery_name, lm.name AS list_monastery
            FROM monastery_members mm
            JOIN monasteries lm ON lm.id = mm.monastery_id
            JOIN priests p ON p.id = mm.priest_id
            LEFT JOIN monasteries m ON m.id = p.monastery_id
            WHERE p.category = ?
        """
        params: list = [category]
        if monastery_id:
            sql += " AND mm.monastery_id = ?"
            params.append(monastery_id)
        sql += f" ORDER BY lm.name, {order_case}, p.surname, p.name"
        cursor.execute(sql, params + rank_order)

        rows = cursor.fetchall()
        conn.close()
        return [(row["list_monastery"], self._row_to_priest(row)) for row in rows]

    def add_monastery_member(self, priest_id: int, monastery_id: int) -> None:
        """Отметить, что человек числится в монастыре (повторный вызов ничего не меняет)"""
        conn = self.get_connection()
        conn.execute(
            "INSERT OR IGNORE INTO monastery_members (priest_id, monastery_id) VALUES (?, ?)",
            (priest_id, monastery_id),
        )
        conn.commit()
        conn.close()

    def sync_monastery_roster(self, monastery_id: int, priest_ids: List[int], categories: List[str]) -> int:
        """
        Список монастыря — источник истины: насельники указанных категорий,
        которых нет в новом списке (выбыли/переведены), из монастыря удаляются.
        Белое духовенство не трогается. Возвращает число удалённых связей.
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        keep = ", ".join("?" for _ in priest_ids) or "NULL"
        cats = ", ".join("?" for _ in categories)
        cursor.execute(f"""
            DELETE FROM monastery_members
            WHERE monastery_id = ?
              AND priest_id NOT IN ({keep})
              AND priest_id IN (SELECT id FROM priests WHERE category IN ({cats}))
        """, [monastery_id, *priest_ids, *categories])
        removed = cursor.rowcount
        # у выбывших основным становится оставшийся монастырь (или никакой)
        cursor.execute("""
            UPDATE priests
            SET monastery_id = (
                SELECT mm.monastery_id FROM monastery_members mm
                WHERE mm.priest_id = priests.id LIMIT 1
            )
            WHERE monastery_id = ?
              AND id NOT IN (SELECT priest_id FROM monastery_members WHERE monastery_id = ?)
        """, (monastery_id, monastery_id))
        conn.commit()
        conn.close()
        return removed

    def find_person(
        self,
        surname: str,
        name: str,
        patronymic: str,
        birth_year: Optional[int],
        categories: Optional[List[str]] = None,
    ) -> Optional[Priest]:
        """
        Поиск уже существующей записи о том же человеке.

        Совпадение по фамилии + имени + отчеству (без учёта регистра) и году рождения:
        одних фамилии и имени недостаточно — в базе встречаются тёзки.
        """
        conn = self.get_connection()
        cursor = conn.cursor()

        sql = f"""
            {_SELECT_PRIESTS}
            WHERE py_lower(p.surname) = py_lower(?)
              AND py_lower(p.name) = py_lower(?)
              AND py_lower(COALESCE(p.patronymic, '')) = py_lower(?)
              AND COALESCE(p.birth_year, CAST(substr(p.birth_date, 1, 4) AS INTEGER)) IS ?
        """
        params: list = [surname, name, patronymic or "", birth_year]
        if categories:
            sql += f" AND p.category IN ({', '.join('?' for _ in categories)})"
            params += categories
        cursor.execute(sql, params)

        row = cursor.fetchone()
        conn.close()
        return self._row_to_priest(row) if row else None

    def set_priest_monastery(self, priest_id: int, monastery_id: Optional[int]) -> bool:
        """Привязка записи к монастырю (или отвязка при monastery_id=None)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE priests SET monastery_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (monastery_id, priest_id),
        )
        success = cursor.rowcount > 0
        if success and monastery_id:
            cursor.execute(
                "INSERT OR IGNORE INTO monastery_members (priest_id, monastery_id) VALUES (?, ?)",
                (priest_id, monastery_id),
            )
        elif success:
            cursor.execute("DELETE FROM monastery_members WHERE priest_id = ?", (priest_id,))
        conn.commit()
        conn.close()
        return success

    def _row_to_priest(self, row: sqlite3.Row) -> Priest:
        """Преобразование строки из БД в объект Priest"""
        keys = set(row.keys())

        def opt(column: str, default=""):
            if column in keys and row[column] is not None:
                return row[column]
            return default

        def parse_date(column: str) -> Optional[date]:
            value = opt(column, None)
            return datetime.strptime(value, "%Y-%m-%d").date() if value else None

        def parse_ts(column: str) -> Optional[datetime]:
            value = opt(column, None)
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S") if value else None

        return Priest(
            id=row["id"],
            name=row["name"],
            patronymic=opt("patronymic"),
            surname=row["surname"],
            birth_date=parse_date("birth_date"),
            birth_place=opt("birth_place"),
            nationality=opt("nationality"),
            status=row["status"],
            name_day=opt("name_day"),
            deacon_ordination_date=parse_date("deacon_ordination_date"),
            priest_ordination_date=parse_date("priest_ordination_date"),
            ordination_date=parse_date("ordination_date"),
            service_place=opt("service_place"),
            education=opt("education"),
            secular_education=opt("secular_education"),
            last_reward=opt("last_reward"),
            phone=opt("phone"),
            category=opt("category", config.CATEGORY_WHITE_CLERGY),
            monastery_id=opt("monastery_id", None),
            monastery_name=opt("monastery_name"),
            monastic_name=opt("monastic_name"),
            obedience=opt("obedience"),
            birth_year=opt("birth_year", None),
            ordination_years=opt("ordination_years"),
            tonsure_date=parse_date("tonsure_date"),
            bishop_ordination_date=parse_date("bishop_ordination_date"),
            created_at=parse_ts("created_at"),
            updated_at=parse_ts("updated_at"),
        )
