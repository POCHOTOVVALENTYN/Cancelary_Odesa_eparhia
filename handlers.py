"""
Обработчики команд и сообщений для Telegram-бота
"""
import asyncio
import logging
from datetime import datetime, date
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import ContextTypes
from typing import List
import database
import models
import utils
import config


async def _handle_unauthorized_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработка сообщений от неадминистраторов:
    - краткое предупреждение
    - автоудаление через 5–10 секунд (сообщения пользователя и предупреждения)
    """
    if not update.message:
        return

    warning = await update.message.reply_text(
        "🚫 <b>Доступ к этому боту ограничен.</b>\n"
        "Бот предназначен только для администраторов. "
        "Пожалуйста, не отправляйте сюда сообщения.",
        parse_mode="HTML",
    )

    async def delete_later():
        await asyncio.sleep(7)
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
            )
        except Exception:
            pass
        try:
            await context.bot.delete_message(
                chat_id=warning.chat_id,
                message_id=warning.message_id,
            )
        except Exception:
            pass

    asyncio.create_task(delete_later())


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    welcome_text = """
👋 <b>Добро пожаловать в бот Канцелярии ОЕУ ОЕ!</b>

Этот бот предоставляет информацию только для администраторов. 
Никто кроме администраторов не может использовать этот бот!🚫


Для начала работы используйте кнопки 👇 ниже
    """

    user_id = update.effective_user.id
    is_admin = utils.is_admin(user_id)

    # Клавиатура с основными действиями (кнопки для пользователя)
    keyboard: List[List[KeyboardButton]] = [
        [KeyboardButton("🔍 Поиск"), KeyboardButton("📋 Список")],
        [KeyboardButton("🎉 Именинники"), KeyboardButton("🏛 Монастыри")],
        [KeyboardButton("❓ Помощь")],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=reply_markup,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    help_text = """
📖 <b>Справка по командам бота</b>

<b>Кнопки:</b>
🔍 Поиск — введите имя, фамилию или монашеское имя
📋 Список — список белого духовенства с постраничной навигацией
🎉 Именинники — просмотр священников по дате рождения, тезоименитства и хиротонии
🏛 Монастыри — насельники, насельницы и духовенство, служащее при монастырях
❓ Помощь — это сообщение
    """
    
    await update.message.reply_text(
        help_text,
        parse_mode="HTML"
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    if not context.args:
        await update.message.reply_text(
            "🔍 <b>Поиск священника</b>\n\n"
            "Использование: /search <имя или фамилия>\n"
            "Пример: /search Иванов",
            parse_mode="HTML"
        )
        return
    
    query = " ".join(context.args)
    db = database.Database()
    priests = db.search_priests(query)
    
    if not priests:
        await update.message.reply_text(
            f"❌ Священники по запросу '{query}' не найдены."
        )
        return
    
    if len(priests) == 1:
        # Если найден один священник, показываем полную информацию
        await update.message.reply_text(
            priests[0].format_message(),
            parse_mode="HTML"
        )
    else:
        # Если найдено несколько, показываем список
        message = f"🔍 <b>Найдено священников: {len(priests)}</b>\n\n"
        for i, priest in enumerate(priests[:20], 1):  # Ограничиваем 20 результатами
            message += f"{i}. {priest.short_title()}\n"
        
        if len(priests) > 20:
            message += f"\n... и ещё {len(priests) - 20} священников"
        
        await update.message.reply_text(
            message,
            parse_mode="HTML"
        )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /list"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    db = database.Database()
    page = int(context.args[0]) if context.args and context.args[0].isdigit() else 0
    
    offset = page * config.ITEMS_PER_PAGE
    # Общий список — белое духовенство; насельники смотрятся в разделе «Монастыри»
    priests = db.get_all_priests(
        limit=config.ITEMS_PER_PAGE, offset=offset, category=config.CATEGORY_WHITE_CLERGY
    )
    total = db.get_total_count(category=config.CATEGORY_WHITE_CLERGY)

    if not priests:
        await update.message.reply_text(
            "📋 Список священников пуст."
        )
        return
    
    header = (
        f"📋 <b>Список священников</b>\n"
        f"Страница {page + 1} из {(total - 1) // config.ITEMS_PER_PAGE + 1}\n\n"
    )

    lines = [header]
    for i, priest in enumerate(priests, 1):
        index = offset + i
        # Полная информация по священнику
        block = f"{index}. {priest.format_message()}"
        lines.append(block)
        lines.append("")  # пустая строка между записями

    message = "\n".join(lines)

    # Создаем кнопки навигации
    keyboard = []
    if page > 0:
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"list_{page - 1}")])
    if offset + len(priests) < total:
        keyboard.append([InlineKeyboardButton("Вперёд ▶️", callback_data=f"list_{page + 1}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    # Сообщение может быть длинным, поэтому разбиваем на части
    parts = utils.split_message(message)
    first = True
    for part in parts:
        if first:
            await update.message.reply_text(
                part,
                parse_mode="HTML",
                reply_markup=reply_markup,
            )
            first = False
        else:
            await update.message.reply_text(
                part,
                parse_mode="HTML",
            )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /status"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    if not context.args:
        status_list = "\n".join([f"• {status}" for status in config.ALL_STATUSES.values()])
        await update.message.reply_text(
            f"📊 <b>Фильтр по статусу</b>\n\n"
            f"Доступные статусы:\n{status_list}\n\n"
            f"Использование: /status &lt;статус&gt;\n"
            f"Пример: /status протоиерей",
            parse_mode="HTML"
        )
        return
    
    status_query = " ".join(context.args)
    normalized_status = utils.validate_status(status_query)
    
    if not normalized_status:
        await update.message.reply_text(
            f"❌ Статус '{status_query}' не найден.\n\n"
            f"Доступные статусы: {', '.join(config.ALL_STATUSES.values())}"
        )
        return
    
    db = database.Database()
    priests = db.get_priests_by_status(normalized_status)
    
    if not priests:
        await update.message.reply_text(
            f"❌ Священники со статусом '{normalized_status}' не найдены."
        )
        return
    
    message = f"📊 <b>Священники со статусом: {normalized_status}</b>\n"
    message += f"Найдено: {len(priests)}\n\n"
    
    for i, priest in enumerate(priests[:50], 1):  # Ограничиваем 50 результатами
        message += f"{i}. {priest.name} {priest.surname}\n"
        if priest.service_place:
            message += f"   Место служения: {priest.service_place}\n"
    
    if len(priests) > 50:
        message += f"\n... и ещё {len(priests) - 50} священников"
    
    # Разбиваем длинное сообщение на части
    parts = utils.split_message(message)
    for part in parts:
        await update.message.reply_text(
            part,
            parse_mode="HTML"
        )


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /add (только для администраторов)"""
    user = update.effective_user
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return
    
    await update.message.reply_text(
        "➕ <b>Добавление нового священника</b>\n\n"
        "Используйте формат:\n"
        "/add\n"
        "Имя: Иван\n"
        "Фамилия: Иванов\n"
        "Дата рождения: 01.01.1980\n"
        "Место рождения: Одесса\n"
        "Статус: Протоиерей\n"
        "Дата рукоположения: 15.05.2005\n"
        "Место служения: Собор Святого Павла\n"
        "Образование: Одесская духовная семинария\n"
        "Последняя награда: Наперсный крест\n\n"
        "Или используйте интерактивный режим, отправив команду /add и следуя инструкциям.",
        parse_mode="HTML"
    )


# ==== Раздел «Монастыри» ====

# Ключ в callback_data -> (категория в БД, тип монастыря, заголовок)
MONASTERY_SECTIONS = {
    "monk": (config.CATEGORY_MONK, "male", "👨 Насельники монастырей"),
    "nun": (config.CATEGORY_NUN, "female", "👩 Насельницы монастырей"),
    "clergy": (config.CATEGORY_WHITE_CLERGY, None, "⛪ Духовенство при монастырях"),
}

MONASTERY_PAGE_SIZE = 30

MONASTERIES_ROOT_TEXT = (
    "🏛 <b>Раздел «Монастыри»</b>\n\n"
    "Выберите категорию:\n"
    "• 👨 Насельники мужских монастырей\n"
    "• 👩 Насельницы женских монастырей\n"
    "• ⛪ Белое духовенство, служащее при монастырях\n\n"
    "Полная карточка — через 🔍 Поиск по фамилии или монашескому имени."
)


def _monasteries_root_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(title, callback_data=f"mon_cat_{key}")]
        for key, (_, _, title) in MONASTERY_SECTIONS.items()
    ]
    rows.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


_MONASTERY_DATE_LABELS = [
    ("tonsure_date", "✂️ Постриг"),
    ("deacon_ordination_date", "✝️ Хиротония в диакона"),
    ("priest_ordination_date", "⛪ Хиротония в иерея"),
    ("bishop_ordination_date", "☦️ Хиротония во епископа"),
]


def _monastery_person_dates(p: models.Priest) -> str:
    """Даты для поздравлений — только те, что известны."""
    line = ""
    if p.name_day:
        line += f"\n    📅 День тезоименитства: {p.name_day}"
    for field_name, label in _MONASTERY_DATE_LABELS:
        d = getattr(p, field_name)
        if d:
            line += f"\n    {label}: {utils.format_date(d)}"
    return line


def _monastery_person_line(index: int, p: models.Priest) -> str:
    """Короткая строка о человеке в списке монастыря."""
    if p.birth_date:
        born = f", род. {utils.format_date(p.birth_date)}"
    elif p.birth_year:
        born = f", {p.birth_year} г.р."
    else:
        born = ""
    if p.is_monastic:
        line = f"{index}. {p.short_title()}"
        if p.is_vicegerent:
            line += " — наместник"
        line += born
        if p.obedience:
            line += f"\n    <i>{p.obedience}</i>"
        # у насельников из списков монастырей только годы; полные даты — из data/*_dates.csv
        return line + _monastery_person_dates(p)
    fio = " ".join(part for part in [p.surname, p.name, p.patronymic] if part)
    line = f"{index}. {p.status} {fio}{born}"
    if p.phone:
        line += f"\n    📞 {p.phone}"
    return line + _monastery_person_dates(p)


async def handle_monasteries_callback(query, context: ContextTypes.DEFAULT_TYPE, data: str):
    """
    callback_data:
      mon_root                      — выбор категории
      mon_cat_<key>                 — выбор монастыря в категории
      mon_list_<key>_<id>_<page>    — список людей (id=0 — все монастыри)
    """
    db = database.Database()

    if data == "mon_root":
        await query.edit_message_text(
            MONASTERIES_ROOT_TEXT, parse_mode="HTML", reply_markup=_monasteries_root_keyboard()
        )
        return

    if data.startswith("mon_cat_"):
        key = data[len("mon_cat_"):]
        if key not in MONASTERY_SECTIONS:
            return
        category, gender, title = MONASTERY_SECTIONS[key]
        monasteries = db.get_monasteries_with_counts(category, gender)
        if not monasteries:
            await query.edit_message_text(
                f"{title}\n\nДанных пока нет. Загрузите списки монастырей: "
                f"<code>python3 import_monasteries.py папка_со_списками</code>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("⬅️ Назад", callback_data="mon_root")]]
                ),
            )
            return

        total = sum(m["count"] for m in monasteries)
        rows = [
            [InlineKeyboardButton(f"{m['name']} ({m['count']})", callback_data=f"mon_list_{key}_{m['id']}_0")]
            for m in monasteries
        ]
        rows.append([InlineKeyboardButton(f"📋 Все ({total})", callback_data=f"mon_list_{key}_0_0")])
        rows.append([
            InlineKeyboardButton("⬅️ Назад", callback_data="mon_root"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ])
        await query.edit_message_text(
            f"<b>{title}</b>\nВсего: {total}\n\nВыберите монастырь:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(rows),
        )
        return

    if data.startswith("mon_list_"):
        try:
            key, monastery_id_str, page_str = data[len("mon_list_"):].rsplit("_", 2)
            monastery_id, page = int(monastery_id_str), int(page_str)
        except ValueError:
            return
        if key not in MONASTERY_SECTIONS:
            return
        category, _, title = MONASTERY_SECTIONS[key]

        # категория насельника уже определяется типом монастыря, фильтр по полу не нужен
        people = db.get_monastery_people(category, monastery_id or None)

        pages = max(1, (len(people) - 1) // MONASTERY_PAGE_SIZE + 1)
        page = min(max(page, 0), pages - 1)
        chunk = people[page * MONASTERY_PAGE_SIZE:(page + 1) * MONASTERY_PAGE_SIZE]

        if monastery_id:
            monastery = db.get_monastery(monastery_id)
            header = f"<b>{title}</b>\n🏛 {monastery['name'] if monastery else ''}\n"
        else:
            header = f"<b>{title}</b> — все монастыри\n"
        header += f"Всего: {len(people)}"
        if pages > 1:
            header += f" · страница {page + 1} из {pages}"

        lines = [header, ""]
        current_monastery = None
        for i, (list_monastery, p) in enumerate(chunk, start=page * MONASTERY_PAGE_SIZE + 1):
            if not monastery_id and list_monastery != current_monastery:
                current_monastery = list_monastery
                lines.append(f"\n<b>🏛 {current_monastery}</b>")
            lines.append(_monastery_person_line(i, p))
        if not chunk:
            lines.append("Никого нет.")

        nav = []
        if page > 0:
            nav.append(InlineKeyboardButton("◀️", callback_data=f"mon_list_{key}_{monastery_id}_{page - 1}"))
        if page < pages - 1:
            nav.append(InlineKeyboardButton("▶️", callback_data=f"mon_list_{key}_{monastery_id}_{page + 1}"))
        keyboard = [nav] if nav else []
        keyboard.append([
            InlineKeyboardButton("⬅️ К монастырям", callback_data=f"mon_cat_{key}"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ])
        reply_markup = InlineKeyboardMarkup(keyboard)

        parts = utils.split_message("\n".join(lines))
        if len(parts) == 1:
            await query.edit_message_text(parts[0], parse_mode="HTML", reply_markup=reply_markup)
        else:
            await query.edit_message_text(parts[0], parse_mode="HTML")
            for part in parts[1:-1]:
                await context.bot.send_message(chat_id=query.message.chat_id, text=part, parse_mode="HTML")
            await context.bot.send_message(
                chat_id=query.message.chat_id, text=parts[-1], parse_mode="HTML", reply_markup=reply_markup
            )
        return


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов от inline-кнопок"""
    query = update.callback_query
    try:
        await query.answer()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Не удалось ответить на callback query (возможно устарел): {e}")
    user = query.from_user
    if not user or not utils.is_admin(user.id):
        # Для неадмина показываем алерт и игнорируем действие
        await query.answer(
            text="🚫 Доступ к этому боту ограничен. Бот предназначен только для администраторов.",
            show_alert=True,
        )
        return

    data = query.data
    
    # Пагинация списка священников
    if data.startswith("list_"):
        page = int(data.split("_")[1])
        db = database.Database()
        offset = page * config.ITEMS_PER_PAGE
        priests = db.get_all_priests(
            limit=config.ITEMS_PER_PAGE, offset=offset, category=config.CATEGORY_WHITE_CLERGY
        )
        total = db.get_total_count(category=config.CATEGORY_WHITE_CLERGY)

        header = (
            f"📋 <b>Список священников</b>\n"
            f"Страница {page + 1} из {(total - 1) // config.ITEMS_PER_PAGE + 1}\n\n"
        )

        lines = [header]
        for i, priest in enumerate(priests, 1):
            index = offset + i
            block = f"{index}. {priest.format_message()}"
            lines.append(block)
            lines.append("")

        message = "\n".join(lines)

        keyboard = []
        if page > 0:
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"list_{page - 1}")])
        if offset + len(priests) < total:
            keyboard.append([InlineKeyboardButton("Вперёд ▶️", callback_data=f"list_{page + 1}")])

        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

        parts = utils.split_message(message)
        chat_id = query.message.chat_id
        first = True
        for part in parts:
            if first:
                await query.edit_message_text(
                    part,
                    parse_mode="HTML",
                    reply_markup=reply_markup,
                )
                first = False
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=part,
                    parse_mode="HTML",
                )
        return

    # Раздел «Монастыри»
    if data.startswith("mon_"):
        await handle_monasteries_callback(query, context, data)
        return

    # Главное меню (из inline-подменю)
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 Главное меню.\nИспользуйте кнопки внизу экрана: "
            "🔍 Поиск, 📋 Список, 🎉 Именинники, 🏛 Монастыри, ❓ Помощь.",
            parse_mode="HTML",
        )
        return

    # Корневое подменю раздела «Именинники»
    if data == "celebrations_root":
        await show_celebrations_root_menu(query)
        return

    # Подменю по типам дат
    if data == "bday_root":
        await show_celebrations_type_menu(query, kind="bday")
        return
    if data == "name_root":
        await show_celebrations_type_menu(query, kind="name")
        return
    if data == "ord_root":
        await show_celebrations_type_menu(query, kind="ord")
        return

    # Именинники на N дней вперёд (по разным типам дат)
    if data.startswith("bday_days_"):
        days_ahead = int(data.split("_")[2])
        await send_celebration_days_report(query, context, kind="bday", days_ahead=days_ahead)
        return
    if data.startswith("name_days_"):
        days_ahead = int(data.split("_")[2])
        await send_celebration_days_report(query, context, kind="name", days_ahead=days_ahead)
        return
    if data.startswith("ord_days_"):
        days_ahead = int(data.split("_")[2])
        await send_celebration_days_report(query, context, kind="ord", days_ahead=days_ahead)
        return

    # Юбилеи по дням (рождение / хиротония)
    if data == "bday_jub_days_menu":
        await query.edit_message_text(
            "🎊 Юбилеи дней рождения — выберите день:",
            reply_markup=_build_days_menu("bday_jub", "bday_root"),
        )
        return
    if data == "ord_jub_days_menu":
        await query.edit_message_text(
            "🏆 Юбилеи хиротонии — выберите день:",
            reply_markup=_build_days_menu("ord_jub", "ord_root"),
        )
        return

    if data.startswith("bday_jub_days_"):
        days_ahead = int(data.split("_")[3])
        await send_celebration_days_report(
            query,
            context,
            kind="bday",
            days_ahead=days_ahead,
            jubilee_only=True,
        )
        return
    if data.startswith("ord_jub_days_"):
        days_ahead = int(data.split("_")[3])
        await send_celebration_days_report(
            query,
            context,
            kind="ord",
            days_ahead=days_ahead,
            jubilee_only=True,
        )
        return

    # Меню месяцев для разных типов
    if data == "bday_month_menu":
        await show_month_menu(query, kind="bday")
        return
    if data == "name_month_menu":
        await show_month_menu(query, kind="name")
        return
    if data == "ord_month_menu":
        await show_month_menu(query, kind="ord")
        return

    # Юбилеи по месяцам (рождение / хиротония)
    if data == "bday_jub_month_menu":
        await show_month_menu_with_prefix(
            query,
            prefix="bday_jub",
            back_callback="bday_root",
            title="🏆 Юбилеи дней рождения — выберите месяц:",
        )
        return
    if data == "ord_jub_month_menu":
        await show_month_menu_with_prefix(
            query,
            prefix="ord_jub",
            back_callback="ord_root",
            title="🏆 Юбилеи хиротонии — выберите месяц:",
        )
        return

    # Именинники по месяцам
    if data.startswith("bday_month_"):
        month = int(data.split("_")[2])
        await send_celebration_month_report(query, context, kind="bday", month=month)
        return
    if data.startswith("name_month_"):
        month = int(data.split("_")[2])
        await send_celebration_month_report(query, context, kind="name", month=month)
        return
    if data.startswith("ord_month_"):
        month = int(data.split("_")[2])
        await send_celebration_month_report(query, context, kind="ord", month=month)
        return

    # Юбилеи по месяцам (callback)
    if data.startswith("bday_jub_month_"):
        month = int(data.split("_")[3])
        await send_celebration_month_report(
            query,
            context,
            kind="bday",
            month=month,
            jubilee_only=True,
        )
        return
    if data.startswith("ord_jub_month_"):
        month = int(data.split("_")[3])
        await send_celebration_month_report(
            query,
            context,
            kind="ord",
            month=month,
            jubilee_only=True,
        )


async def show_celebrations_root_menu(query_or_message):
    """Показывает корневое подменю раздела «Именинники»."""
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🎂 По дате рождения", callback_data="bday_root"),
            ],
            [
                InlineKeyboardButton("🎉 По тезоименитству", callback_data="name_root"),
            ],
            [
                InlineKeyboardButton("✝️ По дате хиротонии", callback_data="ord_root"),
            ],
            [
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
            ],
        ]
    )
    text = (
        "🎉 <b>Раздел «Именинники»</b>\n\n"
        "Выберите, какие даты показать:\n"
        "• 🎂 По дате рождения\n"
        "• 🎉 По тезоименитству\n"
        "• ✝️ По дате хиротонии"
    )
    # query_or_message может быть либо callback_query, либо message
    if isinstance(query_or_message, Update):  # на всякий случай
        await query_or_message.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        # callback_query
        await query_or_message.edit_message_text(text, parse_mode="HTML", reply_markup=keyboard)


def _build_days_menu(prefix: str, back_callback: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора дней (Сегодня, +1...+7)."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Сегодня", callback_data=f"{prefix}_days_0"),
                InlineKeyboardButton("+1 день", callback_data=f"{prefix}_days_1"),
                InlineKeyboardButton("+2 дня", callback_data=f"{prefix}_days_2"),
            ],
            [
                InlineKeyboardButton("+3 дня", callback_data=f"{prefix}_days_3"),
                InlineKeyboardButton("+4 дня", callback_data=f"{prefix}_days_4"),
                InlineKeyboardButton("+5 дней", callback_data=f"{prefix}_days_5"),
            ],
            [
                InlineKeyboardButton("+6 дней", callback_data=f"{prefix}_days_6"),
                InlineKeyboardButton("+7 дней", callback_data=f"{prefix}_days_7"),
            ],
            [
                InlineKeyboardButton("⬅️ Назад", callback_data=back_callback),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
            ],
        ]
    )


def _build_type_menu_keyboard(kind: str) -> InlineKeyboardMarkup:
    """Клавиатура для подменю по конкретному типу дат."""
    prefix = {
        "bday": "bday",
        "name": "name",
        "ord": "ord",
    }[kind]
    extra_rows = []
    if kind in ("bday", "ord"):
        extra_rows = [
            [
                InlineKeyboardButton(
                    "🎊 Юбилеи (по дням)",
                    callback_data=f"{prefix}_jub_days_menu",
                ),
                InlineKeyboardButton(
                    "🏆 Юбилеи (по месяцам)",
                    callback_data=f"{prefix}_jub_month_menu",
                ),
            ]
        ]
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Сегодня", callback_data=f"{prefix}_days_0"),
                InlineKeyboardButton("+1 день", callback_data=f"{prefix}_days_1"),
                InlineKeyboardButton("+2 дня", callback_data=f"{prefix}_days_2"),
            ],
            [
                InlineKeyboardButton("+3 дня", callback_data=f"{prefix}_days_3"),
                InlineKeyboardButton("+4 дня", callback_data=f"{prefix}_days_4"),
                InlineKeyboardButton("+5 дней", callback_data=f"{prefix}_days_5"),
            ],
            [
                InlineKeyboardButton("+6 дней", callback_data=f"{prefix}_days_6"),
                InlineKeyboardButton("+7 дней", callback_data=f"{prefix}_days_7"),
            ],
            [
                InlineKeyboardButton("📅 По месяцам", callback_data=f"{prefix}_month_menu"),
            ],
            *extra_rows,
            [
                InlineKeyboardButton("⬅️ Назад", callback_data="celebrations_root"),
                InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
            ],
        ]
    )


async def show_celebrations_type_menu(query, kind: str):
    """Показывает подменю для конкретного типа (рождение/тезоименитство/хиротония)."""
    titles = {
        "bday": "🎂 Именинники по дате рождения",
        "name": "🎉 Именинники по тезоименитству",
        "ord": "✝️ Именинники по дате хиротонии",
    }
    text = titles.get(kind, "Именинники")
    keyboard = _build_type_menu_keyboard(kind)
    await query.edit_message_text(
        f"{text}\n\nВыберите диапазон:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def show_month_menu(query, kind: str):
    """Показывает меню выбора месяца для указанного типа дат."""
    prefix = {
        "bday": "bday",
        "name": "name",
        "ord": "ord",
    }[kind]
    month_buttons = [
        [
            InlineKeyboardButton("Январь", callback_data=f"{prefix}_month_1"),
            InlineKeyboardButton("Февраль", callback_data=f"{prefix}_month_2"),
            InlineKeyboardButton("Март", callback_data=f"{prefix}_month_3"),
        ],
        [
            InlineKeyboardButton("Апрель", callback_data=f"{prefix}_month_4"),
            InlineKeyboardButton("Май", callback_data=f"{prefix}_month_5"),
            InlineKeyboardButton("Июнь", callback_data=f"{prefix}_month_6"),
        ],
        [
            InlineKeyboardButton("Июль", callback_data=f"{prefix}_month_7"),
            InlineKeyboardButton("Август", callback_data=f"{prefix}_month_8"),
            InlineKeyboardButton("Сентябрь", callback_data=f"{prefix}_month_9"),
        ],
        [
            InlineKeyboardButton("Октябрь", callback_data=f"{prefix}_month_10"),
            InlineKeyboardButton("Ноябрь", callback_data=f"{prefix}_month_11"),
            InlineKeyboardButton("Декабрь", callback_data=f"{prefix}_month_12"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_root"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    await query.edit_message_text(
        "📅 Выберите месяц для просмотра именинников:",
        reply_markup=InlineKeyboardMarkup(month_buttons),
    )


async def show_month_menu_with_prefix(query, prefix: str, back_callback: str, title: str):
    """Показывает меню выбора месяца для заданного префикса callback."""
    month_buttons = [
        [
            InlineKeyboardButton("Январь", callback_data=f"{prefix}_month_1"),
            InlineKeyboardButton("Февраль", callback_data=f"{prefix}_month_2"),
            InlineKeyboardButton("Март", callback_data=f"{prefix}_month_3"),
        ],
        [
            InlineKeyboardButton("Апрель", callback_data=f"{prefix}_month_4"),
            InlineKeyboardButton("Май", callback_data=f"{prefix}_month_5"),
            InlineKeyboardButton("Июнь", callback_data=f"{prefix}_month_6"),
        ],
        [
            InlineKeyboardButton("Июль", callback_data=f"{prefix}_month_7"),
            InlineKeyboardButton("Август", callback_data=f"{prefix}_month_8"),
            InlineKeyboardButton("Сентябрь", callback_data=f"{prefix}_month_9"),
        ],
        [
            InlineKeyboardButton("Октябрь", callback_data=f"{prefix}_month_10"),
            InlineKeyboardButton("Ноябрь", callback_data=f"{prefix}_month_11"),
            InlineKeyboardButton("Декабрь", callback_data=f"{prefix}_month_12"),
        ],
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=back_callback),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    await query.edit_message_text(
        title,
        reply_markup=InlineKeyboardMarkup(month_buttons),
    )


# ==== Даты для «Именинников» ====

# (поле, подпись даты, «лет …») — постриг и епископская хиротония есть только у архиереев
_ORDINATION_EVENTS = [
    ("tonsure_date", "✂️ Постриг в монашество", "в монашестве"),
    ("deacon_ordination_date", "✝️ Дата хиротонии в диакона", "в диаконском сане"),
    ("priest_ordination_date", "⛪ Дата хиротонии в священника", "в священническом сане"),
    ("bishop_ordination_date", "☦️ Дата хиротонии во епископа", "в архиерейском сане"),
]


def _celebration_name(p: models.Priest) -> str:
    fio = " ".join(part for part in [p.surname, p.name, p.patronymic] if part)
    if p.monastic_name:
        return f"{p.status} {p.monastic_name} ({fio})"
    return fio


def _celebration_place(p: models.Priest) -> str:
    return p.service_place or p.monastery_name or "не указано"


def _ord_dates(p: models.Priest) -> List[date]:
    """
    Даты, по которым человек попадает в «Именинники по дате хиротонии».

    Белое духовенство — как раньше: хиротония в священника (или в диакона).
    Монашествующие (архиереи) — каждая дата: постриг и все три хиротонии.
    """
    if p.is_monastic:
        return [getattr(p, f) for f, _, _ in _ORDINATION_EVENTS if getattr(p, f)]
    d = p.priest_ordination_date or p.deacon_ordination_date
    return [d] if d else []


def _has_jubilee(p: models.Priest, kind: str, today: date) -> bool:
    if kind == "bday":
        return utils.is_jubilee(utils.calculate_age(p.birth_date, today))
    if kind == "ord":
        return any(
            utils.is_jubilee(utils.years_since(getattr(p, f), today))
            for f, _, _ in _ORDINATION_EVENTS
        )
    return False


def _rich_celebration_line(idx: int, p: models.Priest, kind: str, today: date) -> str:
    """Подробная строка для отчётов по рождению и хиротонии."""
    age = utils.calculate_age(p.birth_date, today)
    if age is not None:
        age_str = f"{age} лет"
    elif p.birth_year:
        age_str = f"около {today.year - p.birth_year} лет ({p.birth_year} г.р.)"
    else:
        age_str = "возраст не указан"

    jubilee_marks = []
    if utils.is_jubilee(age):
        jubilee_marks.append(f"<b>🎂 ЮБИЛЕЙ возраста: {age} лет</b>")

    birth_line = ""
    if kind == "bday":
        birth_line = f"   📅 Дата рождения: {utils.format_date(p.birth_date)}\n"

    # диакон и священник — всегда (как раньше), постриг и епископ — если известны
    dates_lines = ""
    years_lines = ""
    for field_name, date_label, years_label in _ORDINATION_EVENTS:
        d = getattr(p, field_name)
        if not d and field_name in ("tonsure_date", "bishop_ordination_date"):
            continue
        emoji = date_label.split()[0]
        years = utils.years_since(d, today)
        if kind == "ord":
            dates_lines += f"   {date_label}: {utils.format_date(d)}\n"
        years_lines += f"\n   {emoji} Лет {years_label}: {f'{years} лет' if years is not None else 'нет данных'}"
        if utils.is_jubilee(years):
            jubilee_marks.append(f"<b>{emoji} ЮБИЛЕЙ {years_label}: {years} лет</b>")

    line = (
        f"{idx}. {_celebration_name(p)}\n"
        f"   Сан: {p.status}\n"
        f"{birth_line}"
        f"{dates_lines}"
        f"   🎂 Возраст: {age_str}\n"
        f"   📍 Место служения: {_celebration_place(p)}"
        f"{years_lines}"
    )
    if jubilee_marks:
        line += "\n   🔔 " + " | ".join(jubilee_marks)
    return line


async def send_celebration_days_report(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    days_ahead: int,
    jubilee_only: bool = False,
):
    """Формирует отчёт об именинниках на указанный день для выбранного типа дат."""
    target_date = utils.get_target_date(days_ahead)
    target_ddmm = target_date.strftime("%d.%m")

    db = database.Database()
    priests = db.get_all_priests()

    def match(p: models.Priest) -> bool:
        if kind == "bday":
            if not p.birth_date:
                return False
            return (
                p.birth_date.day == target_date.day
                and p.birth_date.month == target_date.month
            )
        if kind == "name":
            return (p.name_day or "") == target_ddmm
        if kind == "ord":
            return any(d.day == target_date.day and d.month == target_date.month for d in _ord_dates(p))
        return False

    matches = [p for p in priests if match(p)]

    if jubilee_only:
        matches = [p for p in matches if _has_jubilee(p, kind, date.today())]

    # Заголовки по типам
    headers = {
        "bday": "🎂 <b>Именинники по дате рождения на {date}</b>\n\n",
        "name": "🎉 <b>Именинники по тезоименитству на {date}</b>\n\n",
        "ord": "✝️ <b>Именинники по дате хиротонии на {date}</b>\n\n",
    }
    header = headers[kind].format(date=target_date.strftime("%d.%m.%Y"))
    if jubilee_only:
        header = header.replace("Именинники", "Юбилеи")

    if not matches:
        await query.edit_message_text(
            header + "Никто не отмечает в этот день.",
            parse_mode="HTML",
        )
        return

    lines = [header]
    today = date.today()

    for idx, p in enumerate(matches, start=1):
        fio = _celebration_name(p)

        # Специализированный формат для тезоименитств (kind == "name")
        if kind == "name":
            # p.name_day в формате DD.MM
            name_day_str = p.name_day or target_ddmm

            # Текст про день Ангела
            if days_ahead == 0:
                angel_text = "🎉 <b>СЕГОДНЯ ДЕНЬ АНГЕЛА!</b>"
            elif days_ahead == 1:
                angel_text = "🎉 <b>ДЕНЬ АНГЕЛА ЗАВТРА!</b>"
            else:
                angel_text = f"🎉 <b>ДЕНЬ АНГЕЛА ЧЕРЕЗ {days_ahead} ДНЯ(ДНЕЙ)!</b>"

            base_line = (
                f"{idx}. {fio}\n"
                f"   Сан: {p.status}\n"
                f"   📅 День тезоименитства: {name_day_str}\n"
                f"   📍 Место служения: {_celebration_place(p)}\n"
                f"   {angel_text}"
            )
        else:
            base_line = _rich_celebration_line(idx, p, kind, today)

        lines.append(base_line)
        lines.append("")

    message = "\n".join(lines)
    parts = utils.split_message(message)
    chat_id = query.message.chat_id
    first = True
    for part in parts:
        if first:
            await query.edit_message_text(
                part,
                parse_mode="HTML",
            )
            first = False
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=part,
                parse_mode="HTML",
            )


async def send_celebration_month_report(
    query,
    context: ContextTypes.DEFAULT_TYPE,
    kind: str,
    month: int,
    jubilee_only: bool = False,
):
    """Формирует отчёт об именинниках за указанный месяц для выбранного типа дат."""
    month_names = [
        "",
        "Январь",
        "Февраль",
        "Март",
        "Апрель",
        "Май",
        "Июнь",
        "Июль",
        "Август",
        "Сентябрь",
        "Октябрь",
        "Ноябрь",
        "Декабрь",
    ]

    today = date.today()
    year = today.year
    month_name = month_names[month] if 1 <= month <= 12 else str(month)

    db = database.Database()
    priests = db.get_all_priests()

    def match(p: models.Priest) -> bool:
        if kind == "bday":
            if not p.birth_date:
                return False
            return p.birth_date.month == month
        if kind == "name":
            if not p.name_day:
                return False
            try:
                d = datetime.strptime(p.name_day, "%d.%m")
                return d.month == month
            except Exception:
                return False
        if kind == "ord":
            return any(d.month == month for d in _ord_dates(p))
        return False

    matches = [p for p in priests if match(p)]

    if jubilee_only:
        matches = [p for p in matches if _has_jubilee(p, kind, date.today())]

    headers = {
        "bday": "🎂 <b>Именинники по дате рождения за {month} {year} года</b>\n\n",
        "name": "🎉 <b>Именинники по тезоименитству за {month} {year} года</b>\n\n",
        "ord": "✝️ <b>Именинники по дате хиротонии за {month} {year} года</b>\n\n",
    }
    header = headers[kind].format(month=month_name, year=year)
    if jubilee_only:
        header = header.replace("Именинники", "Юбилеи")

    if not matches:
        await query.edit_message_text(
            header + "Никто не отмечает в этом месяце.",
            parse_mode="HTML",
        )
        return

    lines = [header]

    for idx, p in enumerate(matches, start=1):
        fio = _celebration_name(p)

        if kind == "name":
            # Специализированный формат: только день тезоименитства и место служения
            name_day_str = p.name_day or "не указано"
            base_line = (
                f"{idx}. {fio}\n"
                f"   Сан: {p.status}\n"
                f"   📅 День тезоименитства: {name_day_str}\n"
                f"   📍 Место служения: {_celebration_place(p)}"
            )
        else:
            base_line = _rich_celebration_line(idx, p, kind, today)

        lines.append(base_line)
        lines.append("")

    message = "\n".join(lines)
    parts = utils.split_message(message)
    chat_id = query.message.chat_id
    first = True
    for part in parts:
        if first:
            await query.edit_message_text(
                part,
                parse_mode="HTML",
            )
            first = False
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=part,
                parse_mode="HTML",
            )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных текстовых сообщений"""
    text = update.message.text
    user = update.effective_user
    
    logging.getLogger(__name__).info(f"DEBUG: Входящее сообщение от {user.id if user else 'Unknown'}: {text[:50]}")
    
    # Если сообщение начинается с команды, игнорируем (команды обрабатываются отдельно)
    if text.startswith("/"):
        return

    # Полная блокировка для неадминистраторов + антиспам
    if not user or not utils.is_admin(user.id):
        await _handle_unauthorized_message(update, context)
        return

    # Обработка нажатий на клавиатуру (кнопки с эмодзи)
    if text == "🔍 Поиск":
        await update.message.reply_text(
            "🔍 <b>Поиск священника</b>\n\n"
            "Введите имя или фамилию в следующем сообщении.\n"
            "Например: <code>Иванов</code>",
            parse_mode="HTML",
        )
        return

    if text == "📋 Список":
        # Показ первой страницы списка
        context.args = []
        await list_command(update, context)
        return

    if text == "🎉 Именинники":
        # Корневое подменю раздела «Именинники»
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🎂 По дате рождения", callback_data="bday_root")],
                [InlineKeyboardButton("🎉 По тезоименитству", callback_data="name_root")],
                [InlineKeyboardButton("✝️ По дате хиротонии", callback_data="ord_root")],
                [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")],
            ]
        )
        text_root = (
            "🎉 <b>Раздел «Именинники»</b>\n\n"
            "Выберите, какие даты показать:\n"
            "• 🎂 По дате рождения\n"
            "• 🎉 По тезоименитству\n"
            "• ✝️ По дате хиротонии"
        )
        await update.message.reply_text(
            text_root,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        return

    if text == "❓ Помощь":
        await help_command(update, context)
        return

    if text == "🏛 Монастыри":
        await update.message.reply_text(
            MONASTERIES_ROOT_TEXT,
            parse_mode="HTML",
            reply_markup=_monasteries_root_keyboard(),
        )
        return

    # Простой поиск по любому другому тексту
    db = database.Database()
    priests = db.search_priests(text)
    
    if not priests:
        await update.message.reply_text(
            f"❌ По запросу '{text}' ничего не найдено.\n\n"
            f"Используйте команду /search для поиска или /help для справки."
        )
        return
    
    if len(priests) == 1:
        await update.message.reply_text(
            priests[0].format_message(),
            parse_mode="HTML"
        )
    else:
        message = f"🔍 <b>Найдено: {len(priests)}</b>\n\n"
        for i, priest in enumerate(priests[:10], 1):
            message += f"{i}. {priest.short_title()}\n"
        
        if len(priests) > 10:
            message += f"\n... и ещё {len(priests) - 10} результатов"
        
        await update.message.reply_text(
            message,
            parse_mode="HTML"
        )
