"""
Импортёр списков насельников монастырей (отчёты «… мм спис 25» / «… жм спис 25»).

Формат исходных файлов (Word-таблица, одна строка — один человек):
 Код | Сан и монашеское имя | Мирское имя | Год рождения | [Год рукопол. диак., свящ.] |
 Место рождения | Национальность | Образование духовное | Образование светское |
 Последняя награда (мужские) / Послушание (женские)

 - «Сан и монашеское имя»: «Архимандрит / СЕРАФИМ» (иногда без разделителя)
 - «Мирское имя»: «РАКОВСКИЙ / Сергей / Маркович»
 - Годы, а не даты: «1967»; рукоположения — 1–3 года через перенос строки
 - В женских списках колонки рукоположения нет

Название монастыря берётся из заголовка перед таблицей
(«Свято-Успенский Одесский / мужской монастырь / по состоянию на …»).

Поддерживаемые форматы определяются по содержимому, а не по расширению:
 - .docx (в т.ч. сохранённые с расширением .doc) — через python-docx;
 - .rtf и старый .doc (Word 97–2003) — через macOS textutil (только на Mac).
   Если textutil недоступен или таблица не распознана — файл нужно
   пересохранить в Word как .docx.
"""

import csv
import html
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Dict, List, Optional, Tuple

from docx import Document

import config
import utils
from database import Database
from models import Priest

logger = logging.getLogger(__name__)


# Поле -> признаки в заголовке колонки (в нижнем регистре)
HEADER_KEYS = [
    ("rank_name", ("сан",)),
    ("fio", ("мирское",)),
    ("birth_year", ("рожд",)),
    ("ordination", ("рукопол",)),
    ("birth_place", ("место",)),
    ("nationality", ("нацио",)),
    ("education", ("духов",)),
    ("secular_education", ("светск",)),
    ("last_reward", ("наград",)),
    ("obedience", ("послушан",)),
    ("code", ("код",)),
]

EMPTY_VALUES = {"", "-", "–", "—", "нет", "––", "–––", "––––", "----"}


class UnsupportedFileError(Exception):
    """Файл не удаётся прочитать — нужно пересохранить его в .docx"""


@dataclass
class FileResult:
    path: str
    monastery: str = ""
    gender: str = ""
    rows: int = 0
    added: int = 0
    updated: int = 0
    removed: int = 0  # выбыли из списка монастыря (запись о человеке остаётся)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------- Чтение таблиц ----------

class _HtmlTableParser(HTMLParser):
    """Достаёт текст перед первой таблицей и строки всех таблиц из HTML (вывод textutil)."""

    def __init__(self):
        super().__init__()
        self.preamble: List[str] = []
        self.rows: List[List[str]] = []
        self._depth = 0
        self._row: Optional[List[str]] = None
        self._cell: Optional[List[str]] = None
        self._seen_table = False
        self._pre_buf: List[str] = []
        self._skip = 0  # внутри <style>/<title>/<script>

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "title", "script"):
            self._skip += 1
        elif tag == "table":
            self._depth += 1
            if not self._seen_table:
                self._flush_preamble()
            self._seen_table = True
        elif tag == "tr" and self._depth:
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = []
        elif tag in ("br", "p"):
            if self._cell is not None:
                self._cell.append("\n")
            elif not self._seen_table:
                self._flush_preamble()

    def handle_endtag(self, tag):
        if tag in ("style", "title", "script"):
            self._skip = max(0, self._skip - 1)
        elif tag in ("td", "th") and self._cell is not None:
            self._row.append("".join(self._cell))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
        elif tag == "table":
            self._depth -= 1
        elif tag == "p" and not self._seen_table:
            self._flush_preamble()

    def handle_data(self, data):
        if self._skip:
            return
        if self._cell is not None:
            self._cell.append(data)
        elif not self._seen_table:
            self._pre_buf.append(data)

    def _flush_preamble(self):
        text = " ".join("".join(self._pre_buf).split())
        if text:
            self.preamble.append(text)
        self._pre_buf = []


def _detect_format(path: str) -> str:
    with open(path, "rb") as f:
        head = f.read(8)
    if not head:
        raise UnsupportedFileError("файл пустой (0 байт)")
    if head.startswith(b"PK"):
        return "docx"
    if head.startswith(b"{\\rtf"):
        return "rtf"
    if head.startswith(b"\xd0\xcf\x11\xe0"):
        return "doc"
    raise UnsupportedFileError("неизвестный формат файла")


def _read_docx(path: str) -> Tuple[List[str], List[List[str]]]:
    doc = Document(path)
    preamble = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    rows: List[List[str]] = []
    for table in doc.tables:
        for row in table.rows:
            cells: List[str] = []
            prev = None
            for cell in row.cells:
                # объединённые ячейки python-docx возвращает несколько раз
                if cell._tc is prev:
                    continue
                prev = cell._tc
                cells.append(cell.text)
            rows.append(cells)
    return preamble, rows


def _read_via_textutil(path: str) -> Tuple[List[str], List[List[str]]]:
    if not shutil.which("textutil"):
        raise UnsupportedFileError(
            "для .rtf/.doc нужен macOS textutil — запустите импорт на Mac "
            "или пересохраните файл в Word как .docx"
        )
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.html")
        subprocess.run(
            ["textutil", "-convert", "html", "-output", out, path],
            check=True,
            capture_output=True,
        )
        with open(out, encoding="utf-8", errors="replace") as f:
            parser = _HtmlTableParser()
            parser.feed(f.read())
    rows = [[html.unescape(c) for c in r] for r in parser.rows]
    return parser.preamble, rows


def read_tables(path: str) -> Tuple[List[str], List[List[str]]]:
    """Возвращает (строки текста перед таблицей, строки таблицы)."""
    fmt = _detect_format(path)
    if fmt == "docx":
        preamble, rows = _read_docx(path)
    else:
        preamble, rows = _read_via_textutil(path)
    if not rows:
        raise UnsupportedFileError(
            "таблица не распознана — откройте файл в Word и сохраните как .docx"
        )
    return preamble, rows


# ---------- Разбор значений ----------

def _lines(value: str) -> List[str]:
    """Части ячейки: переносы строк и « / » считаются разделителями."""
    parts = re.split(r"\n|\s/\s|/", value or "")
    return [" ".join(p.split()) for p in parts if p and p.strip()]


def _clean(value: str, sep: str = " ") -> str:
    """
    Многострочная ячейка -> одна строка.

    Перенос по дефису («Александро-» + «Грушевский») склеивается без разделителя.
    Запятые составителя («певчая,» / «просфорница») сохраняются; при разделителе-запятой
    висячие запятые убираются, чтобы не было «,,».
    """
    parts: List[str] = []
    for line in _lines(value):
        line = line.rstrip(" ,") if "," in sep else line.rstrip()
        if parts and parts[-1].endswith("-"):
            parts[-1] += line
        elif line:
            parts.append(line)
    text = sep.join(parts)
    return "" if text.lower().strip(" .") in EMPTY_VALUES else text


def _title(word: str) -> str:
    """«СЕРАФИМ» -> «Серафим», «ИОАНН-ПАВЕЛ» -> «Иоанн-Павел»."""
    return "-".join(p.capitalize() for p in word.split("-"))


def parse_rank_and_name(value: str) -> Tuple[str, str]:
    """«Архимандрит / СЕРАФИМ» -> («Архимандрит», «Серафим»)."""
    words = " ".join(_lines(value)).split()
    if not words:
        return "", ""
    status = utils.validate_status(words[0]) or words[0].capitalize()
    monastic_name = " ".join(_title(w) for w in words[1:])
    return status, monastic_name


def parse_fio(value: str) -> Tuple[str, str, str]:
    """«РАКОВСКИЙ / Сергей / Маркович» -> (name, patronymic, surname)."""
    words = " ".join(_lines(value)).split()
    if len(words) < 2:
        return "", "", words[0] if words else ""
    surname = words[0].upper()
    name = _title(words[1])
    patronymic = " ".join(_title(w) for w in words[2:])
    return name, patronymic, surname


def parse_year(value: str) -> Optional[int]:
    match = re.search(r"\b(1[89]\d\d|20\d\d)\b", value or "")
    return int(match.group(1)) if match else None


def parse_years(value: str) -> str:
    """«2003 / 2014» -> «2003, 2014»; прочерк -> «»."""
    return ", ".join(re.findall(r"\b(?:1[89]\d\d|20\d\d)\b", value or ""))


def parse_monastery_title(preamble: List[str], path: str) -> Tuple[str, str]:
    """
    Название и тип монастыря из текста перед таблицей.

    Берутся строки до «по состоянию на …». Тип — по слову «мужской»/«женский»,
    иначе по пометке «мм»/«жм» в имени файла.
    """
    title_lines: List[str] = []
    for line in preamble:
        if "состоянию" in line.lower():
            break
        title_lines.append(" ".join(line.split()))
    name = " ".join(title_lines).strip()

    lowered = (name + " " + os.path.basename(path)).lower()
    if "женск" in lowered or re.search(r"(^|[\s_])жм([\s_]|$)", lowered):
        gender = "female"
    elif "мужск" in lowered or re.search(r"(^|[\s_])мм([\s_]|$)", lowered):
        gender = "male"
    else:
        gender = ""
    return name, gender


def map_columns(header: List[str]) -> Dict[str, int]:
    columns: Dict[str, int] = {}
    for idx, text in enumerate(header):
        low = text.lower()
        for field_name, keys in HEADER_KEYS:
            if field_name not in columns and any(k in low for k in keys):
                columns[field_name] = idx
                break
    return columns


# ---------- Импорт ----------

class MonasteryImporter:
    """Импорт насельников из списков монастырей."""

    def __init__(self, db: Optional[Database] = None, dry_run: bool = False):
        self.db = db or Database()
        self.dry_run = dry_run

    def parse_file(self, path: str) -> Tuple[FileResult, List[Priest]]:
        """Разбор файла без записи в базу."""
        result = FileResult(path=path)
        preamble, rows = read_tables(path)

        result.monastery, result.gender = parse_monastery_title(preamble, path)
        if not result.monastery:
            raise UnsupportedFileError("не найдено название монастыря перед таблицей")
        if not result.gender:
            raise UnsupportedFileError("не удалось определить, мужской или женский монастырь")

        header_idx = next(
            (i for i, r in enumerate(rows) if any("мирское" in c.lower() for c in r)),
            None,
        )
        if header_idx is None:
            raise UnsupportedFileError("не найдена строка заголовков («Мирское имя»)")
        columns = map_columns(rows[header_idx])
        missing = [f for f in ("rank_name", "fio", "birth_year") if f not in columns]
        if missing:
            raise UnsupportedFileError(f"нет обязательных колонок: {', '.join(missing)}")

        category = config.CATEGORY_MONK if result.gender == "male" else config.CATEGORY_NUN
        people: List[Priest] = []

        def cell(row: List[str], field_name: str) -> str:
            idx = columns.get(field_name)
            return row[idx] if idx is not None and idx < len(row) else ""

        for row_no, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
            if not any(c.strip() for c in row):
                continue
            result.rows += 1
            status, monastic_name = parse_rank_and_name(cell(row, "rank_name"))
            name, patronymic, surname = parse_fio(cell(row, "fio"))

            if not status or not name or not surname:
                result.errors.append(
                    f"строка {row_no}: не разобраны сан/ФИО "
                    f"({' '.join(_lines(cell(row, 'rank_name')))} | {' '.join(_lines(cell(row, 'fio')))})"
                )
                continue
            if status not in config.ALL_STATUSES.values():
                result.warnings.append(f"строка {row_no}: нестандартный сан «{status}»")
            if status in config.NOVICE_STATUSES:
                # у послушников в колонке повторено мирское имя
                monastic_name = ""

            people.append(Priest(
                name=name,
                patronymic=patronymic,
                surname=surname,
                status=status,
                category=category,
                monastic_name=monastic_name,
                birth_year=parse_year(cell(row, "birth_year")),
                ordination_years=parse_years(cell(row, "ordination")),
                birth_place=_clean(cell(row, "birth_place"), sep=", "),
                nationality=_clean(cell(row, "nationality")),
                education=_clean(cell(row, "education")),
                secular_education=_clean(cell(row, "secular_education")),
                last_reward=_clean(cell(row, "last_reward")),
                obedience=_clean(cell(row, "obedience")),
            ))
        return result, people

    def import_file(self, path: str) -> FileResult:
        """Разбор и запись одного файла. Повторный импорт обновляет существующие записи."""
        try:
            result, people = self.parse_file(path)
        except UnsupportedFileError as e:
            result = FileResult(path=path)
            result.errors.append(str(e))
            return result

        monastery_id = None
        if not self.dry_run:
            monastery_id = self.db.get_or_create_monastery(result.monastery, result.gender)

        roster_ids: List[int] = []
        for person in people:
            person.monastery_id = monastery_id
            existing = self.db.find_person(
                person.surname,
                person.name,
                person.patronymic,
                person.birth_year,
                categories=[config.CATEGORY_MONK, config.CATEGORY_NUN],
            )
            if existing:
                if existing.monastery_name and result.monastery not in existing.monastery_name.split("; "):
                    # например, архиерей — наместник нескольких обителей: числится в каждой
                    result.warnings.append(
                        f"{person.short_title()}: числится также в «{existing.monastery_name}» — "
                        f"будет показан в каждом из монастырей"
                    )
                if self.dry_run:
                    result.updated += 1
                    continue
                person.id = existing.id
                # основной монастырь не меняем; принадлежность к этому добавится ниже
                person.monastery_id = existing.monastery_id or monastery_id
                # поля, которых нет в монастырских списках, не затираем
                person.phone = existing.phone
                person.name_day = existing.name_day
                person.service_place = existing.service_place
                person.birth_date = existing.birth_date
                person.deacon_ordination_date = existing.deacon_ordination_date
                person.priest_ordination_date = existing.priest_ordination_date
                person.ordination_date = existing.ordination_date
                person.tonsure_date = existing.tonsure_date
                person.bishop_ordination_date = existing.bishop_ordination_date
                self.db.update_priest(person)
                self.db.add_monastery_member(person.id, monastery_id)
                roster_ids.append(person.id)
                result.updated += 1
                continue

            white = self.db.find_person(
                person.surname,
                person.name,
                person.patronymic,
                person.birth_year,
                categories=[config.CATEGORY_WHITE_CLERGY],
            )
            if white:
                result.warnings.append(
                    f"{person.short_title()}: уже есть в базе как {white.status} "
                    f"(id {white.id}) — добавлена отдельная запись, проверьте вручную"
                )
            if not self.dry_run:
                person.id = self.db.add_priest(person)
                self.db.add_monastery_member(person.id, monastery_id)
                roster_ids.append(person.id)
            result.added += 1

        if not self.dry_run and people:
            # кто был в прошлом списке этого монастыря, но нет в новом — выбыл
            result.removed = self.db.sync_monastery_roster(
                monastery_id, roster_ids, [config.CATEGORY_MONK, config.CATEGORY_NUN]
            )
        return result


# ---------- Привязка белого духовенства к монастырям ----------

_GENERIC_PREFIXES = {"свято", "спасо", "св"}
_MONASTERY_WORDS = ("монаст", "м-р", "обител")


def monastery_keywords(name: str) -> List[str]:
    """
    Отличительные основы названия для поиска в «месте служения».

    «Свято-Архангело-Михайловский Одесский мужской монастырь» -> ["михайл"],
    «Женский монастырь в честь иконы … «Целительница» …» -> ["целител"].
    """
    quoted = re.findall(r"[«\"]([^»\"]+)[»\"]", name)
    if quoted:
        return [quoted[0].split()[0].lower()[:7]]
    first_word = name.split()[0] if name.split() else ""
    parts = [p for p in first_word.lower().split("-") if p and p not in _GENERIC_PREFIXES]
    if not parts:
        return []
    return [parts[-1][:6]]


LINK_EXCLUDE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monastery_link_exclude.csv")


def _load_link_exclusions() -> set:
    """Духовенство, которое не нужно привязывать к монастырю, хотя монастырь упомянут в месте служения."""
    if not os.path.exists(LINK_EXCLUDE_PATH):
        return set()
    with open(LINK_EXCLUDE_PATH, encoding="utf-8") as f:
        return {(r["surname"].strip().upper(), r["name"].strip().lower()) for r in csv.DictReader(f)}


def link_white_clergy(db: Database, dry_run: bool = False) -> Dict[str, list]:
    """
    Привязывает белое духовенство к монастырям по полю «место служения».

    Запись привязывается, только если в месте служения есть слово «монастырь»/«м-рь»
    и основа названия ровно одного монастыря. Уже привязанные записи не трогаются.
    Возвращает {'linked': [(priest, monastery_name)], 'unmatched': [priest], 'ambiguous': [priest]}.
    """
    monasteries = db.get_monasteries()
    keyed = [(m, monastery_keywords(m["name"])) for m in monasteries]
    report: Dict[str, list] = {"linked": [], "unmatched": [], "ambiguous": []}
    excluded = _load_link_exclusions()

    for priest in db.get_all_priests(category=config.CATEGORY_WHITE_CLERGY):
        if priest.monastery_id:
            continue
        if (priest.surname.upper(), priest.name.lower()) in excluded:
            continue
        place = " ".join(priest.service_place.lower().split())
        if not any(w in place for w in _MONASTERY_WORDS):
            continue
        # «Свято- Пантелеимоновский», «Константино- Еленинский» — переносы внутри слов
        place_compact = place.replace(" ", "")
        matches = [m for m, keys in keyed if keys and any(k in place_compact for k in keys)]
        if len(matches) == 1:
            report["linked"].append((priest, matches[0]["name"]))
            if not dry_run:
                db.set_priest_monastery(priest.id, matches[0]["id"])
        elif matches:
            report["ambiguous"].append(priest)
        else:
            report["unmatched"].append(priest)
    return report
