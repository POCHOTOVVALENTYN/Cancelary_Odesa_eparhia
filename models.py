"""
Модели данных для базы данных священников
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class Priest:
    """Модель священника"""
    id: Optional[int] = None
    name: str = ""
    patronymic: str = ""
    surname: str = ""
    birth_date: Optional[date] = None
    birth_place: str = ""
    nationality: str = ""
    status: str = ""
    # День тезоименитства (именины) в формате "DD.MM" или пустая строка
    name_day: str = ""
    # Отдельные даты рукоположения
    deacon_ordination_date: Optional[date] = None
    priest_ordination_date: Optional[date] = None
    ordination_date: Optional[date] = None
    service_place: str = ""
    education: str = ""
    secular_education: str = ""
    last_reward: str = ""
    phone: str = ""  # Номер телефона
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {
            "id": self.id,
            "name": self.name,
            "patronymic": self.patronymic,
            "surname": self.surname,
            "birth_date": self.birth_date.isoformat() if self.birth_date else None,
            "birth_place": self.birth_place,
            "nationality": self.nationality,
            "status": self.status,
            "name_day": self.name_day,
            "deacon_ordination_date": self.deacon_ordination_date.isoformat() if self.deacon_ordination_date else None,
            "priest_ordination_date": self.priest_ordination_date.isoformat() if self.priest_ordination_date else None,
            "ordination_date": self.ordination_date.isoformat() if self.ordination_date else None,
            "service_place": self.service_place,
            "education": self.education,
            "secular_education": self.secular_education,
            "last_reward": self.last_reward,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def format_message(self) -> str:
        """Форматирование информации о священнике для отправки в Telegram"""
        full_name_parts = [self.name]
        if self.patronymic:
            full_name_parts.append(self.patronymic)
        full_name_parts.append(self.surname)

        lines = [
            f"<b>👤 {' '.join([p for p in full_name_parts if p])}</b>",
            "",
            f"<b>Статус:</b> {self.status}",
        ]

        if self.nationality:
            lines.append(f"<b>Национальность:</b> {self.nationality}")
        
        if self.birth_date:
            lines.append(f"<b>Дата рождения:</b> {self.birth_date.strftime('%d.%m.%Y')}")

        if self.name_day:
            lines.append(f"<b>День тезоименитства:</b> {self.name_day}")
        
        if self.birth_place:
            lines.append(f"<b>Место рождения:</b> {self.birth_place}")
        
        # Отдельные даты рукоположения
        if self.deacon_ordination_date:
            lines.append(f"<b>Рукоположение в диакона:</b> {self.deacon_ordination_date.strftime('%d.%m.%Y')}")

        if self.priest_ordination_date:
            lines.append(f"<b>Рукоположение в священника:</b> {self.priest_ordination_date.strftime('%d.%m.%Y')}")

        # Общее поле на случай старых данных
        if self.ordination_date and not self.priest_ordination_date:
            lines.append(f"<b>Дата рукоположения:</b> {self.ordination_date.strftime('%d.%m.%Y')}")
        
        if self.service_place:
            lines.append(f"<b>Место служения:</b> {self.service_place}")
        
        if self.education:
            lines.append(f"<b>Образование:</b> {self.education}")

        if self.secular_education:
            lines.append(f"<b>Светское образование:</b> {self.secular_education}")
        
        if self.last_reward:
            lines.append(f"<b>Последняя награда:</b> {self.last_reward}")
        
        if self.phone:
            lines.append(f"<b>📞 Телефон:</b> {self.phone}")
        
        return "\n".join(lines)
