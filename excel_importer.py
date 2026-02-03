"""
Модуль для импорта данных о священниках из Excel файлов
"""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from models import Priest
from database import Database
import utils
import logging

logger = logging.getLogger(__name__)


class ExcelImporter:
    """Класс для импорта данных из Excel файлов"""
    
    # Маппинг возможных названий колонок
    COLUMN_MAPPING = {
        'имя': ['имя', 'name', 'имя священника', 'имя_священника'],
        'фамилия': ['фамилия', 'surname', 'фамилия священника', 'фамилия_священника'],
        'дата рождения': ['дата рождения', 'birth date', 'др', 'дата_рождения', 'birth_date'],
        'место рождения': ['место рождения', 'birth place', 'место_рождения', 'birth_place'],
        'статус': ['статус', 'status', 'сан', 'звание'],
        'дата рукоположения': ['дата рукоположения', 'ordination date', 'дата_рукоположения', 
                               'ordination_date', 'рукоположение'],
        'место служения': ['место служения', 'service place', 'место_служения', 
                          'service_place', 'храм', 'приход'],
        'образование': ['образование', 'education', 'учебное заведение', 'учебное_заведение'],
        'последняя награда': ['последняя награда', 'last reward', 'последняя_награда', 
                             'last_reward', 'награда', 'reward']
    }
    
    def __init__(self, db: Optional[Database] = None):
        """Инициализация импортера"""
        self.db = db or Database()
        self.errors: List[Dict] = []
        self.success_count = 0
        self.total_count = 0
    
    def normalize_column_name(self, column_name: str) -> Optional[str]:
        """Нормализация названия колонки"""
        column_lower = column_name.lower().strip()
        
        for standard_name, variants in self.COLUMN_MAPPING.items():
            if column_lower in variants:
                return standard_name
        
        return None
    
    def read_excel(self, file_path: str) -> pd.DataFrame:
        """Чтение Excel файла"""
        try:
            # Пробуем прочитать первый лист
            df = pd.read_excel(file_path, sheet_name=0, engine='openpyxl')
            
            # Нормализуем названия колонок
            column_mapping = {}
            for col in df.columns:
                normalized = self.normalize_column_name(str(col))
                if normalized:
                    column_mapping[col] = normalized
            
            df = df.rename(columns=column_mapping)
            
            return df
        except Exception as e:
            logger.error(f"Ошибка при чтении Excel файла: {e}")
            raise
    
    def validate_row(self, row: pd.Series, row_number: int) -> Tuple[bool, List[str]]:
        """Валидация строки данных"""
        errors = []
        
        # Проверка обязательных полей
        if pd.isna(row.get('имя')) or str(row.get('имя', '')).strip() == '':
            errors.append("Отсутствует имя")
        
        if pd.isna(row.get('фамилия')) or str(row.get('фамилия', '')).strip() == '':
            errors.append("Отсутствует фамилия")
        
        if pd.isna(row.get('статус')) or str(row.get('статус', '')).strip() == '':
            errors.append("Отсутствует статус")
        else:
            # Валидация статуса
            status = str(row.get('статус', '')).strip()
            normalized_status = utils.validate_status(status)
            if not normalized_status:
                errors.append(f"Неверный статус: {status}")
        
        # Валидация дат
        for date_field in ['дата рождения', 'дата рукоположения']:
            if date_field in row and not pd.isna(row.get(date_field)):
                date_value = row.get(date_field)
                if isinstance(date_value, str):
                    parsed_date = utils.parse_date(date_value)
                    if not parsed_date:
                        errors.append(f"Неверный формат даты для '{date_field}': {date_value}")
                elif isinstance(date_value, datetime):
                    # Excel может читать даты как datetime объекты
                    pass
                elif pd.notna(date_value):
                    # Попытка преобразовать в дату
                    try:
                        pd.to_datetime(date_value)
                    except:
                        errors.append(f"Неверный формат даты для '{date_field}'")
        
        return len(errors) == 0, errors
    
    def row_to_priest(self, row: pd.Series) -> Optional[Priest]:
        """Преобразование строки DataFrame в объект Priest"""
        try:
            # Имя и фамилия
            name = str(row.get('имя', '')).strip()
            surname = str(row.get('фамилия', '')).strip()
            
            if not name or not surname:
                return None
            
            # Дата рождения
            birth_date = None
            if 'дата рождения' in row and pd.notna(row.get('дата рождения')):
                birth_value = row.get('дата рождения')
                if isinstance(birth_value, datetime):
                    birth_date = birth_value.date()
                elif isinstance(birth_value, str):
                    birth_date = utils.parse_date(birth_value)
                else:
                    try:
                        birth_date = pd.to_datetime(birth_value).date()
                    except:
                        pass
            
            # Место рождения
            birth_place = str(row.get('место рождения', '')).strip() if pd.notna(row.get('место рождения')) else ''
            
            # Статус
            status = str(row.get('статус', '')).strip()
            normalized_status = utils.validate_status(status)
            if not normalized_status:
                normalized_status = status  # Оставляем как есть, если не удалось нормализовать
            
            # Дата рукоположения
            ordination_date = None
            if 'дата рукоположения' in row and pd.notna(row.get('дата рукоположения')):
                ord_value = row.get('дата рукоположения')
                if isinstance(ord_value, datetime):
                    ordination_date = ord_value.date()
                elif isinstance(ord_value, str):
                    ordination_date = utils.parse_date(ord_value)
                else:
                    try:
                        ordination_date = pd.to_datetime(ord_value).date()
                    except:
                        pass
            
            # Остальные поля
            service_place = str(row.get('место служения', '')).strip() if pd.notna(row.get('место служения')) else ''
            education = str(row.get('образование', '')).strip() if pd.notna(row.get('образование')) else ''
            last_reward = str(row.get('последняя награда', '')).strip() if pd.notna(row.get('последняя награда')) else ''
            
            return Priest(
                name=name,
                surname=surname,
                birth_date=birth_date,
                birth_place=birth_place,
                status=normalized_status,
                ordination_date=ordination_date,
                service_place=service_place,
                education=education,
                last_reward=last_reward
            )
        except Exception as e:
            logger.error(f"Ошибка при преобразовании строки в Priest: {e}")
            return None
    
    def import_from_file(self, file_path: str, update_existing: bool = False) -> Dict:
        """
        Импорт данных из Excel файла
        
        Args:
            file_path: Путь к Excel файлу
            update_existing: Обновлять ли существующие записи (по имени+фамилии)
        
        Returns:
            Словарь со статистикой импорта
        """
        self.errors = []
        self.success_count = 0
        self.total_count = 0
        
        try:
            # Чтение Excel файла
            df = self.read_excel(file_path)
            self.total_count = len(df)
            
            logger.info(f"Начало импорта из файла {file_path}. Всего строк: {self.total_count}")
            
            # Обработка каждой строки
            for idx, row in df.iterrows():
                row_number = idx + 2  # +2 потому что Excel нумерует с 1 и есть заголовок
                
                # Валидация
                is_valid, validation_errors = self.validate_row(row, row_number)
                
                if not is_valid:
                    self.errors.append({
                        'row': row_number,
                        'errors': validation_errors,
                        'data': row.to_dict()
                    })
                    continue
                
                # Преобразование в объект Priest
                priest = self.row_to_priest(row)
                
                if not priest:
                    self.errors.append({
                        'row': row_number,
                        'errors': ['Не удалось преобразовать данные'],
                        'data': row.to_dict()
                    })
                    continue
                
                # Проверка на дубликаты (если не обновление)
                if not update_existing:
                    existing = self.db.search_priests(f"{priest.name} {priest.surname}")
                    # Проверяем точное совпадение
                    exact_match = any(
                        p.name.lower() == priest.name.lower() and 
                        p.surname.lower() == priest.surname.lower()
                        for p in existing
                    )
                    if exact_match:
                        self.errors.append({
                            'row': row_number,
                            'errors': [f'Священник {priest.name} {priest.surname} уже существует'],
                            'data': row.to_dict()
                        })
                        continue
                
                # Добавление в базу данных
                try:
                    if update_existing:
                        # Поиск существующего священника
                        existing = self.db.search_priests(f"{priest.name} {priest.surname}")
                        exact_match = None
                        for p in existing:
                            if (p.name.lower() == priest.name.lower() and 
                                p.surname.lower() == priest.surname.lower()):
                                exact_match = p
                                break
                        
                        if exact_match:
                            priest.id = exact_match.id
                            self.db.update_priest(priest)
                        else:
                            self.db.add_priest(priest)
                    else:
                        self.db.add_priest(priest)
                    
                    self.success_count += 1
                    logger.info(f"Успешно импортирован: {priest.name} {priest.surname}")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении в БД (строка {row_number}): {e}")
                    self.errors.append({
                        'row': row_number,
                        'errors': [f'Ошибка БД: {str(e)}'],
                        'data': row.to_dict()
                    })
            
            # Формирование результата
            result = {
                'total': self.total_count,
                'success': self.success_count,
                'errors': len(self.errors),
                'error_details': self.errors
            }
            
            logger.info(f"Импорт завершен. Успешно: {self.success_count}, Ошибок: {len(self.errors)}")
            return result
            
        except Exception as e:
            logger.error(f"Критическая ошибка при импорте: {e}")
            raise
    
    def get_error_report(self) -> str:
        """Получение отчета об ошибках в текстовом виде"""
        if not self.errors:
            return "Ошибок не обнаружено."
        
        report = f"Обнаружено ошибок: {len(self.errors)}\n\n"
        
        for error in self.errors[:20]:  # Ограничиваем 20 ошибками
            report += f"Строка {error['row']}:\n"
            for err_msg in error['errors']:
                report += f"  - {err_msg}\n"
            report += "\n"
        
        if len(self.errors) > 20:
            report += f"... и ещё {len(self.errors) - 20} ошибок\n"
        
        return report
