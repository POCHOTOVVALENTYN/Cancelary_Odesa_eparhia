#!/bin/bash
# ============================================
# Скрипт деплоя бота Канцелярии ОЕУ ОЕ
# Для Oracle Linux 9 (micro VM, 1GB RAM)
#
#   ./deploy.sh              — обновить код и перезапустить бота
#   ./deploy.sh --set-token  — дополнительно записать токен из BOT_TOKEN / .env
#
# База данных на сервере — боевая, скрипт её НЕ перезаписывает.
# Перед каждым деплоем на сервере делается резервная копия (~/backups).
#
# Особенность сервера: ответы сервер → Mac длиннее ~1.4 КБ зависают
# (scp-скачивание, длинный вывод). Поэтому файлы только загружаются
# (tar через ssh), а удалённые команды печатают короткие строки;
# подробный вывод pip пишется в $REMOTE_DIR/deploy.log.
# ============================================

set -euo pipefail

SSH_KEY="${SSH_KEY:-/Users/valentin/Cancellary_Bot/keys/ssh-key-2026-04-06.key}"
SERVER="opc@138.2.154.41"
REMOTE_DIR="/home/opc/telegram-bot"
LOCAL_DIR="$(cd "$(dirname "$0")" && pwd)"
SSH=(ssh -o ConnectTimeout=30 -o ServerAliveInterval=60 -o ServerAliveCountMax=5 -o BatchMode=yes -i "$SSH_KEY" "$SERVER")
# Токен хранится в drop-in systemd: SELinux не даёт systemd читать EnvironmentFile из /home
DROPIN_DIR="/etc/systemd/system/telegram-bot.service.d"
DROPIN="$DROPIN_DIR/env.conf"

SET_TOKEN=0
[ "${1:-}" = "--set-token" ] && SET_TOKEN=1

FILES=(
    bot.py handlers.py database.py config.py models.py utils.py
    excel_importer.py excel_template.py kliriki_parser.py
    convert_word_to_excel.py legacy_excel_importer.py
    add_sample_data.py check_diakons.py import_diakons.py
    import_phones_from_kliriki.py offline_import_legacy.py
    reset_and_import_legacy.py test_kliriki_read.py
    monastery_importer.py import_monasteries.py import_vicar_dates.py import_clergy_dates.py
    requirements.txt start.sh
    data/diakons.xlsx data/kliriki.xlsx data/priests_odess.xlsx data/vicar_dates.csv data/clergy_dates.csv
    ИНСТРУКЦИЯ_МОНАСТЫРИ.md
)

echo "🚀 === ДЕПЛОЙ БОТА КАНЦЕЛЯРИИ ОЕУ ОЕ ==="
echo ""

# Шаг 1: Проверка файлов и подключения
echo "📡 Шаг 1: Проверка файлов и SSH подключения..."
cd "$LOCAL_DIR"
for f in "${FILES[@]}"; do
    [ -f "$f" ] || { echo "❌ Нет файла: $f"; exit 1; }
done
"${SSH[@]}" "echo 'SSH OK'; hostname" || { echo "❌ Не удалось подключиться к серверу!"; exit 1; }
echo "✅ Подключение успешно"
echo ""

# Шаг 2: Резервная копия кода и базы на сервере
echo "💾 Шаг 2: Резервная копия на сервере..."
"${SSH[@]}" "set -e; mkdir -p $REMOTE_DIR/data /home/opc/backups
    B=/home/opc/backups/telegram-bot-\$(date +%Y%m%d-%H%M%S).tar.gz
    tar czf \$B -C /home/opc --exclude=venv --exclude=__pycache__ telegram-bot
    chmod 600 \$B; echo \"  ✅ \$B (\$(du -h \$B | cut -f1))\""
echo ""

# Шаг 3: Загрузка файлов (без venv, __pycache__, .git, keys и database.db)
echo "📦 Шаг 3: Загрузка файлов проекта..."
COPYFILE_DISABLE=1 tar czf - "${FILES[@]}" \
    | "${SSH[@]}" "tar xzf - -C $REMOTE_DIR --warning=no-unknown-keyword"
# Сверка контрольных сумм: сервер печатает только несовпадения
shasum -a 256 "${FILES[@]}" \
    | "${SSH[@]}" "cd $REMOTE_DIR && sha256sum -c --quiet - && echo '  ✅ Загружено файлов: ${#FILES[@]}, контрольные суммы совпали'"
echo ""

# Шаг 4: Токен бота
echo "🔑 Шаг 4: Токен бота..."
if [ "$SET_TOKEN" = 0 ] && "${SSH[@]}" "sudo -n test -f $DROPIN"; then
    echo "  ✅ Токен уже настроен ($DROPIN), оставляем как есть"
else
    TOKEN="${BOT_TOKEN:-}"
    if [ -z "$TOKEN" ] && [ -f "$LOCAL_DIR/.env" ]; then
        TOKEN="$(sed -n 's/^BOT_TOKEN=//p' "$LOCAL_DIR/.env" | tr -d "\"' \r")"
    fi
    [ -n "$TOKEN" ] || { echo "❌ Токен не найден: задайте BOT_TOKEN или BOT_TOKEN=... в .env"; exit 1; }
    # Токен передаётся через stdin, чтобы не попасть в список процессов
    printf '%s' "$TOKEN" | "${SSH[@]}" "set -e; T=\$(cat)
        sudo -n mkdir -p $DROPIN_DIR
        printf '[Service]\nEnvironment=\"BOT_TOKEN=%s\"\n' \"\$T\" | sudo -n tee $DROPIN >/dev/null
        sudo -n chmod 600 $DROPIN"
    echo "  ✅ Токен записан в $DROPIN"
fi
echo ""

# Шаг 5: Python окружение и зависимости (по одной, чтобы не перегрузить RAM)
echo "🐍 Шаг 5: Python окружение и зависимости..."
"${SSH[@]}" "cd $REMOTE_DIR && { [ -d venv ] || python3 -m venv venv; }"
for pkg in $(grep -vE '^\s*(#|$)' requirements.txt); do
    "${SSH[@]}" "cd $REMOTE_DIR && venv/bin/pip install -q '$pkg' >> deploy.log 2>&1 \
        || { echo '❌ $pkg — см. $REMOTE_DIR/deploy.log'; exit 1; }"
    echo "  ✅ $pkg"
done
"${SSH[@]}" "cd $REMOTE_DIR && venv/bin/python3 -c 'import telegram, openpyxl, pandas, docx, config, database, handlers, monastery_importer' && echo '  ✅ Все импорты проходят'"
echo ""

# Шаг 6: systemd сервис
echo "⚙️ Шаг 6: Настройка systemd сервиса..."
"${SSH[@]}" "sudo -n tee /etc/systemd/system/telegram-bot.service > /dev/null" << 'SERVICEEOF'
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
SERVICEEOF
echo "✅ Сервис настроен"
echo ""

# Шаг 7: Перезапуск и проверка
echo "🤖 Шаг 7: Перезапуск бота..."
# --no-block: на перегруженном сервере restart может висеть минутами вместе с ssh;
# результат проверяем ниже по журналу
OLD_ID="$("${SSH[@]}" "systemctl show -p InvocationID --value telegram-bot")"
"${SSH[@]}" "sudo -n systemctl daemon-reload && sudo -n systemctl enable -q telegram-bot && sudo -n systemctl restart --no-block telegram-bot"
# Ждём до 3 мин строку «Application started» в журнале именно нового запуска
# ("active" в systemd значит лишь, что процесс жив, а не что бот подключился)
STARTED="$("${SSH[@]}" "for i in \$(seq 90); do
        ID=\$(systemctl show -p InvocationID --value telegram-bot)
        [ -n \"\$ID\" ] && [ \"\$ID\" != '$OLD_ID' ] \
            && sudo -n journalctl _SYSTEMD_INVOCATION_ID=\$ID -o cat | grep -q 'Application started' && { echo yes; exit; }
        sleep 2
    done; echo no")"
STATE="$("${SSH[@]}" "systemctl is-active telegram-bot" || true)"
echo "📊 Статус: $STATE, подключение к Telegram: $([ "$STARTED" = yes ] && echo есть || echo НЕТ)"
echo "📋 Логи запуска:"
"${SSH[@]}" "ID=\$(systemctl show -p InvocationID --value telegram-bot)
    sudo -n journalctl _SYSTEMD_INVOCATION_ID=\$ID --no-pager -o cat \
    | grep -v getUpdates | tail -6 | sed -E 's/bot[0-9]+:[A-Za-z0-9_-]+/bot<TOKEN>/g' | cut -c1-110"
echo ""

if [ "$STATE" != "active" ] || [ "$STARTED" != yes ]; then
    echo "❌ Бот не запущен. Подробности: ssh ... 'sudo journalctl -u telegram-bot -n 50'"
    echo "   Откат: распаковать последнюю копию из /home/opc/backups и перезапустить сервис"
    exit 1
fi

echo "🎉 === ДЕПЛОЙ ЗАВЕРШЁН УСПЕШНО ==="
echo ""
echo "Полезные команды для сервера:"
echo "  Статус:      ssh -i $SSH_KEY $SERVER 'systemctl is-active telegram-bot'"
echo "  Логи:        ssh -i $SSH_KEY $SERVER 'sudo journalctl -u telegram-bot -n 20 --no-pager | cut -c1-150'"
echo "  Перезапуск:  ssh -i $SSH_KEY $SERVER 'sudo systemctl restart telegram-bot'"
echo "  Остановка:   ssh -i $SSH_KEY $SERVER 'sudo systemctl stop telegram-bot'"
