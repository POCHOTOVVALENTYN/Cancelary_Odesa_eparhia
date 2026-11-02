"""
Главный файл Telegram-бота для Одесской Епархии
"""
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
import config
import handlers

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
# httpx пишет в INFO каждый опрос Telegram — это ~300 строк в час в журнале
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    """Главная функция запуска бота"""
    # Проверка токена
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("ОШИБКА: Не установлен токен бота!")
        logger.error("Пожалуйста, установите переменную окружения BOT_TOKEN или измените config.py")
        return
    
    # Создание приложения
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Регистрация обработчиков команд
    application.add_handler(CommandHandler("start", handlers.start_command))
    application.add_handler(CommandHandler("help", handlers.help_command))
    application.add_handler(CommandHandler("search", handlers.search_command))
    application.add_handler(CommandHandler("list", handlers.list_command))
    application.add_handler(CommandHandler("status", handlers.status_command))
    application.add_handler(CommandHandler("add", handlers.add_command))
    
    # Обработчик callback-запросов (для inline-кнопок)
    application.add_handler(CallbackQueryHandler(handlers.callback_handler))
    
    # Обработчик текстовых сообщений (должен быть последним)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.message_handler))
    
    # Инициализация базы данных
    import database
    database.get_db()
    logger.info("База данных инициализирована")

    # Запуск бота: боту нужны только сообщения и нажатия inline-кнопок
    logger.info("Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=[Update.MESSAGE, Update.CALLBACK_QUERY])


if __name__ == "__main__":
    main()
