#!/bin/bash
# ============================================
# Скрипт деплоя бота Канцелярии ОЕУ ОЕ
# Для Oracle Linux 9 (micro VM, 1GB RAM)
# ============================================

set -e

SSH_KEY="/Users/valentin/Cancellary_Bot/keys/ssh-key-2026-04-06.key"
SERVER="opc@138.2.154.41"
SSH_CMD="ssh -o ConnectTimeout=30 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -i $SSH_KEY $SERVER"
SCP_CMD="scp -o ConnectTimeout=30 -o ServerAliveInterval=60 -i $SSH_KEY"
REMOTE_DIR="/home/opc/telegram-bot"
LOCAL_DIR="/Users/valentin/Cancellary_Bot"

echo "🚀 === ДЕПЛОЙ БОТА КАНЦЕЛЯРИИ ОЕУ ОЕ ==="
echo ""

# Шаг 1: Проверка подключения
echo "📡 Шаг 1: Проверка SSH подключения..."
$SSH_CMD "echo 'SSH OK'; hostname" || { echo "❌ Не удалось подключиться к серверу!"; exit 1; }
echo "✅ Подключение успешно"
echo ""

# Шаг 2: Создание директории
echo "📁 Шаг 2: Создание рабочей директории..."
$SSH_CMD "mkdir -p $REMOTE_DIR/data"
echo "✅ Директория создана"
echo ""

# Шаг 3: Копирование файлов (без venv, __pycache__, .git, keys)
echo "📦 Шаг 3: Копирование файлов проекта..."
# Основные Python файлы
for f in bot.py handlers.py database.py config.py models.py utils.py \
         excel_importer.py excel_template.py kliriki_parser.py \
         convert_word_to_excel.py legacy_excel_importer.py \
         add_sample_data.py check_diakons.py import_diakons.py \
         import_phones_from_kliriki.py offline_import_legacy.py \
         reset_and_import_legacy.py test_kliriki_read.py \
         requirements.txt start.sh; do
    if [ -f "$LOCAL_DIR/$f" ]; then
        $SCP_CMD "$LOCAL_DIR/$f" "$SERVER:$REMOTE_DIR/$f"
        echo "  ✅ $f"
    fi
done

# Копирование базы данных
echo "  📊 Копирование базы данных..."
$SCP_CMD "$LOCAL_DIR/database.db" "$SERVER:$REMOTE_DIR/database.db"
echo "  ✅ database.db"

# Копирование папки data
if [ -d "$LOCAL_DIR/data" ]; then
    echo "  📂 Копирование папки data..."
    $SCP_CMD -r "$LOCAL_DIR/data/"* "$SERVER:$REMOTE_DIR/data/" 2>/dev/null || true
    echo "  ✅ data/"
fi

echo "✅ Файлы скопированы"
echo ""

# Шаг 4: Настройка Python окружения (БЕЗ dnf — экономим RAM!)
echo "🐍 Шаг 4: Настройка Python окружения..."
$SSH_CMD "cd $REMOTE_DIR && python3 -m venv venv && source venv/bin/activate && pip install --upgrade pip"
echo "✅ venv создан"
echo ""

# Шаг 5: Установка зависимостей (по одной, чтобы не перегрузить RAM)
echo "📥 Шаг 5: Установка зависимостей..."
$SSH_CMD "cd $REMOTE_DIR && source venv/bin/activate && pip install 'python-telegram-bot==20.7'"
echo "  ✅ python-telegram-bot"
$SSH_CMD "cd $REMOTE_DIR && source venv/bin/activate && pip install 'openpyxl==3.1.2'"
echo "  ✅ openpyxl"
$SSH_CMD "cd $REMOTE_DIR && source venv/bin/activate && pip install 'python-docx==1.1.0'"
echo "  ✅ python-docx"
# pandas ставим последним — он самый тяжёлый
$SSH_CMD "cd $REMOTE_DIR && source venv/bin/activate && pip install 'pandas==2.1.4'"
echo "  ✅ pandas"
echo "✅ Все зависимости установлены"
echo ""

# Шаг 6: Тестовый запуск (проверка импортов)
echo "🧪 Шаг 6: Проверка импортов..."
$SSH_CMD "cd $REMOTE_DIR && source venv/bin/activate && python3 -c 'import telegram; import openpyxl; import pandas; import docx; print(\"ALL IMPORTS OK\")'"
echo "✅ Все импорты проходят"
echo ""

# Шаг 7: Создание systemd service
echo "⚙️ Шаг 7: Настройка systemd сервиса..."
$SSH_CMD "sudo tee /etc/systemd/system/telegram-bot.service > /dev/null << 'SERVICEEOF'
[Unit]
Description=Telegram Bot Cancellary OEU OE
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=opc
Group=opc
WorkingDirectory=/home/opc/telegram-bot
ExecStart=/home/opc/telegram-bot/venv/bin/python3 /home/opc/telegram-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

# Ограничения ресурсов для micro VM
MemoryMax=400M
MemoryHigh=300M

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
SERVICEEOF"

echo "✅ Сервис создан"
echo ""

# Шаг 8: Запуск бота
echo "🤖 Шаг 8: Запуск бота..."
$SSH_CMD "sudo systemctl daemon-reload && sudo systemctl enable telegram-bot && sudo systemctl start telegram-bot"
sleep 3
echo "✅ Бот запущен"
echo ""

# Шаг 9: Проверка статуса
echo "📊 Шаг 9: Проверка статуса..."
$SSH_CMD "sudo systemctl status telegram-bot --no-pager"
echo ""

# Шаг 10: Последние логи
echo "📋 Последние логи:"
$SSH_CMD "sudo journalctl -u telegram-bot -n 20 --no-pager"
echo ""

echo "🎉 === ДЕПЛОЙ ЗАВЕРШЁН УСПЕШНО ==="
echo "🤖 Бот должен отвечать в Telegram!"
echo ""
echo "Полезные команды для сервера:"
echo "  Статус:      $SSH_CMD 'sudo systemctl status telegram-bot'"
echo "  Логи:        $SSH_CMD 'sudo journalctl -u telegram-bot -f'"
echo "  Перезапуск:  $SSH_CMD 'sudo systemctl restart telegram-bot'"
echo "  Остановка:   $SSH_CMD 'sudo systemctl stop telegram-bot'"
