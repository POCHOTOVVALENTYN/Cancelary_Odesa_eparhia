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
    # Категория: white_clergy | monk | nun (см. config.CATEGORIES)
    category: str = "white_clergy"
    # Монастырь: для насельников — место пребывания, для белого духовенства — место служения при монастыре
    monastery_id: Optional[int] = None
    monastery_name: str = ""  # только для чтения (из JOIN с monasteries)
    monastic_name: str = ""   # монашеское имя, например «Серафим»
    obedience: str = ""       # послушание (в списках женских монастырей)
    # В монастырских списках указаны только годы, без дня и месяца
    birth_year: Optional[int] = None
    ordination_years: str = ""  # например «2003, 2014»
    # Для монашествующих архиереев (даты из «даты поздравлений викарии»)
    tonsure_date: Optional[date] = None           # постриг в монашество
    bishop_ordination_date: Optional[date] = None  # хиротония во епископа
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def is_monastic(self) -> bool:
        return self.category in ("monk", "nun")

    @property
    def is_vicegerent(self) -> bool:
        """Архиерей в монастырском списке — наместник обители"""
        return self.category == "monk" and self.status in ("Архиепископ", "Епископ")

    def short_title(self) -> str:
        """Краткая строка для списков: «Архимандрит Серафим (Раковский)» или «Иван Иванов - Иерей»."""
        if self.monastic_name:
            return f"{self.status} {self.monastic_name} ({self.surname.capitalize()})"
        if self.is_monastic:
            return f"{self.status} {self.name} {self.surname.capitalize()}"
        return f"{self.name} {self.surname} - {self.status}"

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
            "category": self.category,
            "monastery_id": self.monastery_id,
            "monastery_name": self.monastery_name,
            "monastic_name": self.monastic_name,
            "obedience": self.obedience,
            "birth_year": self.birth_year,
            "ordination_years": self.ordination_years,
            "tonsure_date": self.tonsure_date.isoformat() if self.tonsure_date else None,
            "bishop_ordination_date": self.bishop_ordination_date.isoformat() if self.bishop_ordination_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def format_message(self) -> str:
        """Форматирование информации о священнике для отправки в Telegram"""
        full_name_parts = [self.name]
        if self.patronymic:
            full_name_parts.append(self.patronymic)
        full_name_parts.append(self.surname)

        full_name = ' '.join([p for p in full_name_parts if p])
        if self.monastic_name:
            title = f"{self.status} {self.monastic_name} ({full_name})"
        else:
            title = full_name

        lines = [
            f"<b>👤 {title}</b>",
            "",
            f"<b>Статус:</b> {self.status}",
        ]

        if self.is_monastic and self.monastery_name:
            if self.is_vicegerent:
                label = "Наместник"
            else:
                label = "Насельник" if self.category == "monk" else "Насельница"
            lines.append(f"<b>{label}:</b> {self.monastery_name}")

        if self.nationality:
            lines.append(f"<b>Национальность:</b> {self.nationality}")

        if self.birth_date:
            lines.append(f"<b>Дата рождения:</b> {self.birth_date.strftime('%d.%m.%Y')}")
        elif self.birth_year:
            lines.append(f"<b>Год рождения:</b> {self.birth_year}")

        if self.name_day:
            lines.append(f"<b>День тезоименитства:</b> {self.name_day}")
        
        if self.birth_place:
            lines.append(f"<b>Место рождения:</b> {self.birth_place}")
        
        if self.tonsure_date:
            lines.append(f"<b>Постриг в монашество:</b> {self.tonsure_date.strftime('%d.%m.%Y')}")

        # Отдельные даты рукоположения
        if self.deacon_ordination_date:
            lines.append(f"<b>Рукоположение в диакона:</b> {self.deacon_ordination_date.strftime('%d.%m.%Y')}")

        if self.priest_ordination_date:
            lines.append(f"<b>Рукоположение в священника:</b> {self.priest_ordination_date.strftime('%d.%m.%Y')}")

        # Общее поле на случай старых данных
        if self.ordination_date and not self.priest_ordination_date:
            lines.append(f"<b>Дата рукоположения:</b> {self.ordination_date.strftime('%d.%m.%Y')}")

        if self.bishop_ordination_date:
            lines.append(f"<b>Хиротония во епископа:</b> {self.bishop_ordination_date.strftime('%d.%m.%Y')}")

        if self.ordination_years and not (self.deacon_ordination_date or self.priest_ordination_date):
            lines.append(f"<b>Годы рукоположения:</b> {self.ordination_years}")

        if self.service_place:
            lines.append(f"<b>Место служения:</b> {self.service_place}")

        if not self.is_monastic and self.monastery_name:
            lines.append(f"<b>Служит при монастыре:</b> {self.monastery_name}")

        if self.obedience:
            lines.append(f"<b>Послушание:</b> {self.obedience}")
        
        if self.education:
            lines.append(f"<b>Образование:</b> {self.education}")

        if self.secular_education:
            lines.append(f"<b>Светское образование:</b> {self.secular_education}")
        
        if self.last_reward:
            lines.append(f"<b>Последняя награда:</b> {self.last_reward}")
        
        if self.phone:
            lines.append(f"<b>📞 Телефон:</b> {self.phone}")
        
        return "\n".join(lines)
