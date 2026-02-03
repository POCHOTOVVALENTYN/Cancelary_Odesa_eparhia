# Детальная инструкция по развертыванию бота на Oracle Linux

## Обзор

Эта инструкция специально для Oracle Linux (пользователь `opc`). Все команды адаптированы под этот дистрибутив.

## Шаг 1: Подключение к серверу

### 1.1. Подключение через SSH

```bash
ssh -i /Users/valentin/Downloads/Cancelary_ssh-key.key opc@92.5.40.131
```

После успешного подключения вы увидите:
```
[opc@instance-name ~]$
```

### 1.2. Проверка системы

```bash
# Проверка версии Oracle Linux
cat /etc/oracle-release

# Проверка версии ядра
uname -r

# Проверка доступного места на диске
df -h
```

## Шаг 2: Обновление системы

### 2.1. Обновление пакетов

```bash
# Обновление списка пакетов
sudo yum update -y

# Или если используется dnf (в новых версиях)
sudo dnf update -y
```

### 2.2. Установка необходимых инструментов

```bash
# Установка базовых инструментов
sudo yum install -y git wget curl vim

# Или через dnf
sudo dnf install -y git wget curl vim
```

## Шаг 3: Установка Python 3

### 3.1. Проверка наличия Python

```bash
# Проверка версии Python (если уже установлен)
python3 --version

# Или
python --version
```

### 3.2. Установка Python 3.8+ (если не установлен)

```bash
# Установка Python 3 и pip
sudo yum install -y python3 python3-pip python3-devel

# Или через dnf
sudo dnf install -y python3 python3-pip python3-devel

# Проверка установки
python3 --version
pip3 --version
```

### 3.3. Обновление pip

```bash
python3 -m pip install --upgrade pip
```

## Шаг 4: Загрузка проекта на сервер

### Вариант A: Через SCP (с вашего локального Mac)

**На вашем локальном компьютере** выполните:

```bash
# Создание директории на сервере (если нужно)
ssh -i /Users/valentin/Downloads/Cancelary_ssh-key.key opc@92.5.40.131 "mkdir -p ~/telegram-bot"

# Копирование всех файлов проекта
scp -i /Users/valentin/Downloads/Cancelary_ssh-key.key -r /Users/valentin/Cancellary_Bot/* opc@92.5.40.131:~/telegram-bot/

# Или копирование всей директории
scp -i /Users/valentin/Downloads/Cancelary_ssh-key.key -r /Users/valentin/Cancellary_Bot opc@92.5.40.131:~/
```

### Вариант B: Через Git (если проект в репозитории)

**На сервере** выполните:

```bash
# Клонирование репозитория
cd ~
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> telegram-bot
cd telegram-bot
```

### Вариант C: Через wget/curl (если файлы на веб-сервере)

```bash
# Скачивание архива проекта
cd ~
wget <URL_АРХИВА>
tar -xzf archive.tar.gz
mv extracted_folder telegram-bot
cd telegram-bot
```

## Шаг 5: Настройка проекта на сервере

### 5.1. Переход в директорию проекта

```bash
cd ~/telegram-bot
ls -la
```

Убедитесь, что все файлы на месте:
- `bot.py`
- `handlers.py`
- `database.py`
- `config.py`
- `requirements.txt`
- и т.д.

### 5.2. Создание виртуального окружения

```bash
# Создание виртуального окружения
python3 -m venv venv

# Активация виртуального окружения
source venv/bin/activate

# Проверка (в начале строки должно появиться (venv))
which python
```

### 5.3. Установка зависимостей

```bash
# Обновление pip в виртуальном окружении
pip install --upgrade pip

# Установка зависимостей из requirements.txt
pip install -r requirements.txt

# Проверка установки
pip list
```

Должны быть установлены:
- python-telegram-bot
- openpyxl
- pandas
- python-docx

### 5.4. Настройка конфигурации

```bash
# Редактирование config.py
nano config.py
```

Убедитесь, что:
- `BOT_TOKEN` установлен правильно
- `ADMIN_IDS` содержит правильные ID администраторов:
  ```python
  ADMIN_IDS: List[int] = [
      830196453,
      534966512,
      751473735,
  ]
  ```

**Важно для безопасности**: Рекомендуется использовать переменные окружения вместо хранения токена в файле.

### 5.5. Настройка переменных окружения (рекомендуется)

```bash
# Создание файла для переменных окружения
nano ~/.env

# Добавьте строку:
BOT_TOKEN=ваш_токен_здесь

# Загрузка переменных окружения
export BOT_TOKEN="ваш_токен_здесь"
```

Или создайте файл `/etc/systemd/system/telegram-bot.env` (будет использоваться systemd).

### 5.6. Создание директории для данных

```bash
# Создание директории data (если её нет)
mkdir -p ~/telegram-bot/data

# Установка прав доступа
chmod 755 ~/telegram-bot/data
```

### 5.7. Импорт данных (если есть файл Excel)

```bash
# Если у вас есть файл priests_odess.xlsx, загрузите его в data/
# Затем выполните импорт
cd ~/telegram-bot
source venv/bin/activate
python3 reset_and_import_legacy.py
```

## Шаг 6: Тестовый запуск бота

### 6.1. Проверка работоспособности

```bash
cd ~/telegram-bot
source venv/bin/activate

# Тестовый запуск (для проверки)
python3 bot.py
```

Если всё работает, вы увидите:
```
INFO - База данных инициализирована
INFO - Бот запущен и готов к работе!
```

**Нажмите Ctrl+C** для остановки тестового запуска.

### 6.2. Проверка в Telegram

Откройте Telegram и проверьте, что бот отвечает на команды.

## Шаг 7: Настройка systemd для автозапуска

### 7.1. Создание systemd service файла

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте следующее содержимое (адаптировано для Oracle Linux):

```ini
[Unit]
Description=Telegram Bot for Odessa Eparchy
After=network.target

[Service]
Type=simple
User=opc
Group=opc
WorkingDirectory=/home/opc/telegram-bot
Environment="PATH=/home/opc/telegram-bot/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="BOT_TOKEN=ваш_токен_здесь"
ExecStart=/home/opc/telegram-bot/venv/bin/python3 /home/opc/telegram-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=telegram-bot

# Безопасность
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

**Важно**: Замените `ваш_токен_здесь` на реальный токен или удалите строку `Environment="BOT_TOKEN=..."`, если используете `config.py`.

### 7.2. Альтернативный вариант с файлом .env

Если хотите использовать файл `.env`:

```bash
# Создание файла окружения для systemd
sudo nano /etc/systemd/system/telegram-bot.env
```

Добавьте:
```
BOT_TOKEN=ваш_токен_здесь
```

Затем в service файле замените:
```ini
EnvironmentFile=/etc/systemd/system/telegram-bot.env
```

Вместо:
```ini
Environment="BOT_TOKEN=ваш_токен_здесь"
```

### 7.3. Активация и запуск сервиса

```bash
# Перезагрузка systemd для чтения нового сервиса
sudo systemctl daemon-reload

# Включение автозапуска при загрузке системы
sudo systemctl enable telegram-bot

# Запуск бота
sudo systemctl start telegram-bot

# Проверка статуса
sudo systemctl status telegram-bot
```

Вы должны увидеть:
```
● telegram-bot.service - Telegram Bot for Odessa Eparchy
   Loaded: loaded (/etc/systemd/system/telegram-bot.service; enabled; vendor preset: disabled)
   Active: active (running) since ...
```

### 7.4. Просмотр логов

```bash
# Просмотр логов в реальном времени
sudo journalctl -u telegram-bot -f

# Последние 100 строк логов
sudo journalctl -u telegram-bot -n 100

# Логи с временными метками
sudo journalctl -u telegram-bot --since "1 hour ago"
```

## Шаг 8: Настройка файрвола (firewalld)

Oracle Linux использует `firewalld` по умолчанию.

### 8.1. Проверка статуса файрвола

```bash
# Проверка статуса
sudo firewall-cmd --state

# Просмотр активных зон
sudo firewall-cmd --list-all
```

### 8.2. Настройка файрвола (если нужно)

```bash
# Разрешение SSH (обычно уже разрешено)
sudo firewall-cmd --permanent --add-service=ssh

# Перезагрузка файрвола
sudo firewall-cmd --reload

# Проверка правил
sudo firewall-cmd --list-all
```

**Примечание**: Для Telegram-бота не нужно открывать дополнительные порты, так как бот сам подключается к серверам Telegram.

## Шаг 9: Настройка резервного копирования

### 9.1. Создание скрипта резервного копирования

```bash
nano ~/backup_bot.sh
```

Добавьте:

```bash
#!/bin/bash
BACKUP_DIR="/home/opc/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Резервная копия базы данных
if [ -f /home/opc/telegram-bot/database.db ]; then
    cp /home/opc/telegram-bot/database.db $BACKUP_DIR/database_$DATE.db
    echo "Database backed up: database_$DATE.db"
fi

# Резервная копия конфигурации
if [ -f /home/opc/telegram-bot/config.py ]; then
    cp /home/opc/telegram-bot/config.py $BACKUP_DIR/config_$DATE.py
    echo "Config backed up: config_$DATE.py"
fi

# Резервная копия данных (если есть)
if [ -d /home/opc/telegram-bot/data ]; then
    tar -czf $BACKUP_DIR/data_$DATE.tar.gz -C /home/opc/telegram-bot data/
    echo "Data directory backed up: data_$DATE.tar.gz"
fi

# Удаление старых резервных копий (старше 7 дней)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.py" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Сделать скрипт исполняемым
chmod +x ~/backup_bot.sh

# Тестовый запуск
~/backup_bot.sh
```

### 9.2. Настройка cron для автоматического резервного копирования

```bash
# Открытие crontab
crontab -e
```

Добавьте строку (резервное копирование каждый день в 3:00):

```
0 3 * * * /home/opc/backup_bot.sh >> /home/opc/backup.log 2>&1
```

Проверка crontab:
```bash
crontab -l
```

## Шаг 10: Мониторинг и обслуживание

### 10.1. Полезные команды для управления ботом

```bash
# Проверка статуса
sudo systemctl status telegram-bot

# Перезапуск бота
sudo systemctl restart telegram-bot

# Остановка бота
sudo systemctl stop telegram-bot

# Запуск бота
sudo systemctl start telegram-bot

# Просмотр логов
sudo journalctl -u telegram-bot -f

# Последние 50 строк логов
sudo journalctl -u telegram-bot -n 50
```

### 10.2. Проверка использования ресурсов

```bash
# Использование CPU и памяти
top
# или
htop  # (если установлен: sudo yum install htop -y)

# Использование диска
df -h

# Использование памяти
free -h
```

### 10.3. Обновление бота

```bash
cd ~/telegram-bot

# Если используете Git
git pull

# Активация виртуального окружения
source venv/bin/activate

# Обновление зависимостей (если requirements.txt изменился)
pip install -r requirements.txt --upgrade

# Перезапуск сервиса
sudo systemctl restart telegram-bot

# Проверка логов
sudo journalctl -u telegram-bot -f
```

## Шаг 11: Безопасность

### 11.1. Обновление системы

```bash
# Регулярное обновление
sudo yum update -y

# Или через dnf
sudo dnf update -y
```

### 11.2. Настройка автоматических обновлений безопасности

```bash
# Установка yum-cron (для автоматических обновлений)
sudo yum install -y yum-cron

# Включение автоматических обновлений безопасности
sudo systemctl enable yum-cron
sudo systemctl start yum-cron

# Или для dnf
sudo dnf install -y dnf-automatic
sudo systemctl enable --now dnf-automatic.timer
```

### 11.3. Настройка SSH (усиление безопасности)

```bash
# Редактирование конфигурации SSH
sudo nano /etc/ssh/sshd_config
```

Рекомендуемые настройки:
```
PasswordAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
```

Перезапуск SSH:
```bash
sudo systemctl restart sshd
```

### 11.4. Настройка SELinux (если включен)

```bash
# Проверка статуса SELinux
getenforce

# Если SELinux в режиме Enforcing, может потребоваться настройка контекстов
# Для systemd сервисов обычно не требуется дополнительных действий
```

## Шаг 12: Устранение неполадок

### 12.1. Бот не запускается

```bash
# Проверка логов на ошибки
sudo journalctl -u telegram-bot -n 100 | grep -i error

# Проверка прав доступа к файлам
ls -la /home/opc/telegram-bot/

# Проверка токена в systemd
sudo systemctl show telegram-bot | grep BOT_TOKEN

# Проверка работоспособности Python
cd /home/opc/telegram-bot
source venv/bin/activate
python3 bot.py
```

### 12.2. Бот падает или перезапускается

```bash
# Просмотр логов с временными метками
sudo journalctl -u telegram-bot --since "10 minutes ago"

# Проверка использования ресурсов
top

# Проверка доступности интернета
ping -c 3 api.telegram.org
```

### 12.3. Проблемы с базой данных

```bash
# Проверка прав доступа к базе данных
ls -la /home/opc/telegram-bot/database.db

# Проверка размера базы данных
du -h /home/opc/telegram-bot/database.db

# Резервное копирование перед исправлением
cp /home/opc/telegram-bot/database.db /home/opc/telegram-bot/database_backup.db
```

### 12.4. Проблемы с зависимостями

```bash
# Переустановка зависимостей
cd /home/opc/telegram-bot
source venv/bin/activate
pip install --upgrade -r requirements.txt --force-reinstall
```

## Шаг 13: Дополнительные настройки

### 13.1. Настройка ротации логов

```bash
# Создание конфигурации для ротации логов
sudo nano /etc/logrotate.d/telegram-bot
```

Добавьте:
```
/var/log/telegram-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 opc opc
}
```

### 13.2. Настройка мониторинга (опционально)

Можно настроить простой мониторинг через cron:

```bash
# Создание скрипта проверки
nano ~/check_bot.sh
```

Добавьте:
```bash
#!/bin/bash
if ! systemctl is-active --quiet telegram-bot; then
    echo "Bot is down! Restarting..."
    sudo systemctl restart telegram-bot
    echo "Bot restarted at $(date)" >> ~/bot_restarts.log
fi
```

```bash
chmod +x ~/check_bot.sh

# Добавление в crontab (проверка каждые 5 минут)
crontab -e
```

Добавьте:
```
*/5 * * * * /home/opc/check_bot.sh
```

## Проверочный список после развертывания

- [ ] Бот запущен и работает (`sudo systemctl status telegram-bot`)
- [ ] Бот отвечает в Telegram на команды
- [ ] Автозапуск включен (`sudo systemctl is-enabled telegram-bot`)
- [ ] Резервное копирование настроено и работает
- [ ] Логи доступны (`sudo journalctl -u telegram-bot`)
- [ ] Система обновлена (`sudo yum update`)
- [ ] Файрвол настроен (если нужно)
- [ ] SSH безопасно настроен

## Заключение

После выполнения всех шагов ваш бот будет работать 24/7 на сервере Oracle Linux. Бот автоматически перезапустится при перезагрузке сервера и при сбоях благодаря systemd.

Для проверки работы бота:
1. Откройте Telegram
2. Найдите вашего бота
3. Отправьте команду `/start`
4. Проверьте, что бот отвечает

## Полезные ссылки

- Документация Oracle Linux: https://docs.oracle.com/en/operating-systems/oracle-linux/
- Документация systemd: https://www.freedesktop.org/software/systemd/man/systemd.service.html
- Документация python-telegram-bot: https://python-telegram-bot.org/
