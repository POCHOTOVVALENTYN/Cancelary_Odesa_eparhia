"""
Модуль для работы с базой данных
"""
import sqlite3
from datetime import date, datetime
from typing import List, Optional
from models import Priest
import config


class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получение соединения с базой данных"""
        conn = sqlite3.connect(self.db_path)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
        ]

        for column_name, column_type in migrations:
            if column_name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE priests ADD COLUMN {column_name} {column_type}"
                )
        
        conn.commit()
        conn.close()
    
    def add_priest(self, priest: Priest) -> int:
        """Добавление нового священника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO priests (
                name,
                patronymic,
                surname,
                birth_date,
                birth_place,
                nationality,
                status,
                name_day,
                deacon_ordination_date,
                priest_ordination_date,
                ordination_date,
                service_place,
                education,
                secular_education,
                last_reward,
                phone
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            priest.name,
            priest.patronymic,
            priest.surname,
            priest.birth_date.isoformat() if priest.birth_date else None,
            priest.birth_place,
            priest.nationality,
            priest.status,
            priest.name_day,
            priest.deacon_ordination_date.isoformat() if priest.deacon_ordination_date else None,
            priest.priest_ordination_date.isoformat() if priest.priest_ordination_date else None,
            priest.ordination_date.isoformat() if priest.ordination_date else None,
            priest.service_place,
            priest.education,
            priest.secular_education,
            priest.last_reward,
            priest.phone
        ))
        
        priest_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return priest_id
    
    def get_priest_by_id(self, priest_id: int) -> Optional[Priest]:
        """Получение священника по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM priests WHERE id = ?", (priest_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return self._row_to_priest(row)
        return None
    
    def search_priests(self, query: str) -> List[Priest]:
        """Поиск священников по имени, фамилии или полному ФИО"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        search_term = f"%{query.lower()}%"
        cursor.execute("""
            SELECT * FROM priests 
            WHERE LOWER(name) LIKE ?
               OR LOWER(surname) LIKE ?
               OR LOWER(surname || ' ' || name || ' ' || COALESCE(patronymic, '')) LIKE ?
            ORDER BY surname, name
        """, (search_term, search_term, search_term))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_priest(row) for row in rows]
    
    def get_all_priests(self, limit: Optional[int] = None, offset: int = 0) -> List[Priest]:
        """Получение всех священников с пагинацией"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if limit:
            cursor.execute("""
                SELECT * FROM priests 
                ORDER BY surname, name
                LIMIT ? OFFSET ?
            """, (limit, offset))
        else:
            cursor.execute("""
                SELECT * FROM priests 
                ORDER BY surname, name
            """)
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_priest(row) for row in rows]
    
    def get_priests_by_status(self, status: str) -> List[Priest]:
        """Получение священников по статусу"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM priests 
            WHERE LOWER(status) = LOWER(?)
            ORDER BY surname, name
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
        
        cursor.execute("""
            UPDATE priests 
            SET 
                name = ?,
                patronymic = ?,
                surname = ?,
                birth_date = ?,
                birth_place = ?,
                nationality = ?,
                status = ?,
                name_day = ?,
                deacon_ordination_date = ?,
                priest_ordination_date = ?,
                ordination_date = ?,
                service_place = ?,
                education = ?,
                secular_education = ?,
                last_reward = ?,
                phone = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            priest.name,
            priest.patronymic,
            priest.surname,
            priest.birth_date.isoformat() if priest.birth_date else None,
            priest.birth_place,
            priest.nationality,
            priest.status,
            priest.name_day,
            priest.deacon_ordination_date.isoformat() if priest.deacon_ordination_date else None,
            priest.priest_ordination_date.isoformat() if priest.priest_ordination_date else None,
            priest.ordination_date.isoformat() if priest.ordination_date else None,
            priest.service_place,
            priest.education,
            priest.secular_education,
            priest.last_reward,
            priest.phone,
            priest.id
        ))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def delete_priest(self, priest_id: int) -> bool:
        """Удаление священника"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM priests WHERE id = ?", (priest_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_total_count(self) -> int:
        """Получение общего количества священников"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM priests")
        count = cursor.fetchone()["count"]
        conn.close()
        
        return count
    
    def _row_to_priest(self, row: sqlite3.Row) -> Priest:
        """Преобразование строки из БД в объект Priest"""
        birth_date = None
        if row["birth_date"]:
            birth_date = datetime.strptime(row["birth_date"], "%Y-%m-%d").date()
        
        ordination_date = None
        if row["ordination_date"]:
            ordination_date = datetime.strptime(row["ordination_date"], "%Y-%m-%d").date()

        deacon_ordination_date = None
        if "deacon_ordination_date" in row.keys() and row["deacon_ordination_date"]:
            deacon_ordination_date = datetime.strptime(row["deacon_ordination_date"], "%Y-%m-%d").date()

        priest_ordination_date = None
        if "priest_ordination_date" in row.keys() and row["priest_ordination_date"]:
            priest_ordination_date = datetime.strptime(row["priest_ordination_date"], "%Y-%m-%d").date()
        
        created_at = None
        if row["created_at"]:
            created_at = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S")
        
        updated_at = None
        if row["updated_at"]:
            updated_at = datetime.strptime(row["updated_at"], "%Y-%m-%d %H:%M:%S")
        
        return Priest(
            id=row["id"],
            name=row["name"],
            patronymic=row["patronymic"] or "",
            surname=row["surname"],
            birth_date=birth_date,
            birth_place=row["birth_place"] or "",
            nationality=row["nationality"] or "" if "nationality" in row.keys() else "",
            status=row["status"],
            name_day=row["name_day"] or "" if "name_day" in row.keys() else "",
            deacon_ordination_date=deacon_ordination_date,
            priest_ordination_date=priest_ordination_date,
            ordination_date=ordination_date,
            service_place=row["service_place"] or "",
            education=row["education"] or "",
            secular_education=row["secular_education"] or "" if "secular_education" in row.keys() else "",
            last_reward=row["last_reward"] or "",
            phone=row["phone"] or "" if "phone" in row.keys() else "",
            created_at=created_at,
            updated_at=updated_at
        )
