"""
Скрипт для добавления тестовых данных в базу данных
"""
from datetime import date
from database import Database
from models import Priest


def add_sample_data():
    """Добавление примеров данных о священниках"""
    db = Database()
    
    sample_priests = [
        Priest(
            name="Иван",
            surname="Иванов",
            birth_date=date(1980, 1, 15),
            birth_place="Одесса",
            status="Протоиерей",
            ordination_date=date(2005, 5, 20),
            service_place="Свято-Успенский кафедральный собор",
            education="Одесская духовная семинария",
            last_reward="Наперсный крест"
        ),
        Priest(
            name="Петр",
            surname="Петров",
            birth_date=date(1975, 3, 10),
            birth_place="Киев",
            status="Иерей",
            ordination_date=date(2000, 6, 15),
            service_place="Храм Святого Николая",
            education="Киевская духовная академия",
            last_reward="Камилавка"
        ),
        Priest(
            name="Александр",
            surname="Сидоров",
            birth_date=date(1990, 7, 25),
            birth_place="Одесса",
            status="Диакон",
            ordination_date=date(2015, 9, 10),
            service_place="Храм Святого Георгия",
            education="Одесская духовная семинария",
            last_reward=""
        ),
        Priest(
            name="Михаил",
            surname="Козлов",
            birth_date=date(1985, 11, 5),
            birth_place="Харьков",
            status="Протодиакон",
            ordination_date=date(2010, 4, 12),
            service_place="Свято-Троицкий храм",
            education="Харьковская духовная семинария",
            last_reward="Двойной орарь"
        ),
        Priest(
            name="Сергей",
            surname="Волков",
            birth_date=date(1978, 2, 18),
            birth_place="Одесса",
            status="Протоиерей",
            ordination_date=date(2003, 8, 25),
            service_place="Храм Святой Марии Магдалины",
            education="Одесская духовная семинария",
            last_reward="Наперсный крест с украшениями"
        ),
    ]
    
    print("Добавление тестовых данных...")
    for priest in sample_priests:
        priest_id = db.add_priest(priest)
        print(f"✓ Добавлен священник: {priest.name} {priest.surname} (ID: {priest_id})")
    
    print(f"\nВсего добавлено священников: {len(sample_priests)}")
    print("Тестовые данные успешно добавлены в базу данных!")


if __name__ == "__main__":
    add_sample_data()
