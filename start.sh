#!/bin/bash

# Скрипт для запуска бота Одесской Епархии

echo "🚀 Запуск Telegram-бота для Одесской Епархии"
echo ""

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "🔧 Активация виртуального окружения..."
source venv/bin/activate

# Проверка установки зависимостей
if ! python -c "import telegram" 2>/dev/null; then
    echo "📥 Установка зависимостей..."
    pip install -r requirements.txt
fi

# Загрузка переменных окружения из .env (если файл есть)
if [ -f ".env" ]; then
    echo "🔑 Загрузка переменных из .env..."
    set -a
    source .env
    set +a
fi

# Проверка токена
if [ -z "$BOT_TOKEN" ]; then
    echo "❌ ОШИБКА: Переменная окружения BOT_TOKEN не установлена!"
    echo "   Установите её командой: export BOT_TOKEN='ваш_токен'"
    echo "   Или создайте файл .env по образцу .env.example"
    exit 1
fi

# Запуск бота
echo "▶️  Запуск бота..."
python bot.py
