"""
Обработчики команд и сообщений для Telegram-бота
"""
import asyncio
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
        [KeyboardButton("🎉 Именинники")],
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
🔍 Поиск — введите имя или фамилию для поиска священника  
📋 Список — список всех священников с постраничной навигацией  
🎉 Именинники — просмотр священников по дате рождения, тезоименитства и хиротонии  
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
            message += f"{i}. {priest.name} {priest.surname} - {priest.status}\n"
        
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
    priests = db.get_all_priests(limit=config.ITEMS_PER_PAGE, offset=offset)
    total = db.get_total_count()
    
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
        status_list = "\n".join([f"• {status}" for status in config.PRIEST_STATUSES.values()])
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
            f"Доступные статусы: {', '.join(config.PRIEST_STATUSES.values())}"
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


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback-запросов от inline-кнопок"""
    query = update.callback_query
    await query.answer()
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
        priests = db.get_all_priests(limit=config.ITEMS_PER_PAGE, offset=offset)
        total = db.get_total_count()

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

    # Главное меню (из inline-подменю)
    if data == "main_menu":
        await query.edit_message_text(
            "🏠 Главное меню.\nИспользуйте кнопки внизу экрана: "
            "🔍 Поиск, 📋 Список, 🎉 Именинники, ❓ Помощь.",
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


def _build_type_menu_keyboard(kind: str) -> InlineKeyboardMarkup:
    """Клавиатура для подменю по конкретному типу дат."""
    prefix = {
        "bday": "bday",
        "name": "name",
        "ord": "ord",
    }[kind]
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


async def send_celebration_days_report(
    query, context: ContextTypes.DEFAULT_TYPE, kind: str, days_ahead: int
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
            ord_date = p.priest_ordination_date or p.deacon_ordination_date
            if not ord_date:
                return False
            return ord_date.day == target_date.day and ord_date.month == target_date.month
        return False

    matches = [p for p in priests if match(p)]

    # Заголовки по типам
    headers = {
        "bday": "🎂 <b>Именинники по дате рождения на {date}</b>\n\n",
        "name": "🎉 <b>Именинники по тезоименитству на {date}</b>\n\n",
        "ord": "✝️ <b>Именинники по дате хиротонии на {date}</b>\n\n",
    }
    header = headers[kind].format(date=target_date.strftime("%d.%m.%Y"))

    if not matches:
        await query.edit_message_text(
            header + "Никто не отмечает в этот день.",
            parse_mode="HTML",
        )
        return

    lines = [header]
    today = date.today()

    for idx, p in enumerate(matches, start=1):
        fio = " ".join([part for part in [p.surname, p.name, p.patronymic] if part])

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
                f"   📍 Место служения: {p.service_place or 'не указано'}\n"
                f"   {angel_text}"
            )
        else:
            # Универсальный «богатый» формат для рождения и хиротонии
            age = utils.calculate_age(p.birth_date, today)
            age_str = f"{age} лет" if age is not None else "возраст не указан"
            age_jubilee = utils.is_jubilee(age)

            years_deacon = utils.years_since(p.deacon_ordination_date, today)
            years_priest = utils.years_since(p.priest_ordination_date, today)

            deacon_str = (
                f"{years_deacon} лет" if years_deacon is not None else "нет данных"
            )
            priest_str = (
                f"{years_priest} лет" if years_priest is not None else "нет данных"
            )

            jubilee_marks = []
            if age_jubilee:
                jubilee_marks.append(f"<b>🎂 ЮБИЛЕЙ возраста: {age} лет</b>")
            if utils.is_jubilee(years_deacon):
                jubilee_marks.append(
                    f"<b>✝️ ЮБИЛЕЙ в диаконском сане: {years_deacon} лет</b>"
                )
            if utils.is_jubilee(years_priest):
                jubilee_marks.append(
                    f"<b>⛪ ЮБИЛЕЙ в священническом сане: {years_priest} лет</b>"
                )

            base_line = (
                f"{idx}. {fio}\n"
                f"   Сан: {p.status}\n"
                f"   🎂 Возраст: {age_str}\n"
                f"   📍 Место служения: {p.service_place or 'не указано'}\n"
                f"   ✝️ Лет в диаконском сане: {deacon_str}\n"
                f"   ⛪ Лет в священническом сане: {priest_str}"
            )

            if jubilee_marks:
                base_line += "\n   🔔 " + " | ".join(jubilee_marks)

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
    query, context: ContextTypes.DEFAULT_TYPE, kind: str, month: int
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
            ord_date = p.priest_ordination_date or p.deacon_ordination_date
            if not ord_date:
                return False
            return ord_date.month == month
        return False

    matches = [p for p in priests if match(p)]

    headers = {
        "bday": "🎂 <b>Именинники по дате рождения за {month} {year} года</b>\n\n",
        "name": "🎉 <b>Именинники по тезоименитству за {month} {year} года</b>\n\n",
        "ord": "✝️ <b>Именинники по дате хиротонии за {month} {year} года</b>\n\n",
    }
    header = headers[kind].format(month=month_name, year=year)

    if not matches:
        await query.edit_message_text(
            header + "Никто не отмечает в этом месяце.",
            parse_mode="HTML",
        )
        return

    lines = [header]

    for idx, p in enumerate(matches, start=1):
        fio = " ".join([part for part in [p.surname, p.name, p.patronymic] if part])

        if kind == "name":
            # Специализированный формат: только день тезоименитства и место служения
            name_day_str = p.name_day or "не указано"
            base_line = (
                f"{idx}. {fio}\n"
                f"   Сан: {p.status}\n"
                f"   📅 День тезоименитства: {name_day_str}\n"
                f"   📍 Место служения: {p.service_place or 'не указано'}"
            )
        else:
            # Универсальный «богатый» формат для рождения и хиротонии
            age = utils.calculate_age(p.birth_date, today)
            age_str = f"{age} лет" if age is not None else "возраст не указан"
            age_jubilee = utils.is_jubilee(age)

            years_deacon = utils.years_since(p.deacon_ordination_date, today)
            years_priest = utils.years_since(p.priest_ordination_date, today)

            deacon_str = (
                f"{years_deacon} лет" if years_deacon is not None else "нет данных"
            )
            priest_str = (
                f"{years_priest} лет" if years_priest is not None else "нет данных"
            )

            jubilee_marks = []
            if age_jubilee:
                jubilee_marks.append(f"<b>🎂 ЮБИЛЕЙ возраста: {age} лет</b>")
            if utils.is_jubilee(years_deacon):
                jubilee_marks.append(
                    f"<b>✝️ ЮБИЛЕЙ в диаконском сане: {years_deacon} лет</b>"
                )
            if utils.is_jubilee(years_priest):
                jubilee_marks.append(
                    f"<b>⛪ ЮБИЛЕЙ в священническом сане: {years_priest} лет</b>"
                )

            birth_line = ""
            if kind == "bday":
                birth_line = f"   📅 Дата рождения: {utils.format_date(p.birth_date)}\n"

            base_line = (
                f"{idx}. {fio}\n"
                f"   Сан: {p.status}\n"
                f"{birth_line}"
                f"   🎂 Возраст: {age_str}\n"
                f"   📍 Место служения: {p.service_place or 'не указано'}\n"
                f"   ✝️ Лет в диаконском сане: {deacon_str}\n"
                f"   ⛪ Лет в священническом сане: {priest_str}"
            )

            if jubilee_marks:
                base_line += "\n   🔔 " + " | ".join(jubilee_marks)

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
            message += f"{i}. {priest.name} {priest.surname} - {priest.status}\n"
        
        if len(priests) > 10:
            message += f"\n... и ещё {len(priests) - 10} результатов"
        
        await update.message.reply_text(
            message,
            parse_mode="HTML"
        )
