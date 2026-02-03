# Инструкция по развертыванию бота на Oracle Cloud Infrastructure (OCI)

## Обзор

Эта инструкция поможет вам развернуть Telegram-бота для Одесской Епархии на сервере Oracle Cloud, чтобы он работал 24/7.

## Предварительные требования

1. **Аккаунт Oracle Cloud** (бесплатный tier доступен)
   - Регистрация: https://www.oracle.com/cloud/free/
   - Требуется кредитная карта (но не списываются средства на бесплатном tier)

2. **Доступ к проекту бота** (локально на вашем компьютере)

3. **Токен Telegram-бота** (уже должен быть в `config.py`)

## Шаг 1: Создание виртуальной машины (VM) в Oracle Cloud

### 1.1. Вход в Oracle Cloud Console

1. Откройте https://cloud.oracle.com/
2. Войдите в свой аккаунт
3. Выберите ваш **Tenancy** (аренда)

### 1.2. Создание VM Instance

1. В меню найдите **"Compute" → "Instances"**
2. Нажмите **"Create Instance"**

### 1.3. Настройка VM

**Основные параметры:**

- **Name**: `telegram-bot-odessa-eparchy` (или любое другое имя)
- **Image**: Выберите **"Canonical Ubuntu 22.04"** или **"Oracle Linux 8"**
- **Shape**: Для бесплатного tier выберите **"VM.Standard.E2.1.Micro"** (1 OCPU, 1 GB RAM)
- **Networking**: Оставьте по умолчанию (создаст VCN автоматически)
- **SSH Keys**: 
  - Выберите **"Generate a key pair for me"** или загрузите свой публичный ключ
  - **ВАЖНО**: Сохраните приватный ключ, если генерируете новый!

3. Нажмите **"Create"**

### 1.4. Ожидание создания VM

- Подождите 2-3 минуты, пока VM создастся
- Запишите **Public IP address** (он понадобится для подключения)

## Шаг 2: Подключение к серверу

### 2.1. Через SSH (macOS/Linux)

```bash
# Если вы использовали сгенерированный ключ Oracle
chmod 400 /path/to/your/private_key.key
ssh -i /path/to/your/private_key.key ubuntu@<PUBLIC_IP>

# Или если вы загрузили свой ключ
ssh ubuntu@<PUBLIC_IP>
```

### 2.2. Через SSH (Windows)

Используйте **PuTTY** или **Windows Terminal**:

1. В PuTTY:
   - Host Name: `ubuntu@<PUBLIC_IP>`
   - Connection → SSH → Auth → Credentials: загрузите приватный ключ
   - Нажмите "Open"

## Шаг 3: Настройка сервера

### 3.1. Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### 3.2. Установка Python и необходимых инструментов

```bash
# Установка Python 3.10+
sudo apt install python3 python3-pip python3-venv git -y

# Проверка версии
python3 --version
```

### 3.3. Создание пользователя для бота (опционально, но рекомендуется)

```bash
# Создание пользователя
sudo adduser botuser
sudo usermod -aG sudo botuser

# Переключение на нового пользователя
su - botuser
```

## Шаг 4: Загрузка проекта на сервер

### Вариант A: Через Git (рекомендуется)

#### 4.1. На вашем локальном компьютере

```bash
cd /Users/valentin/Cancellary_Bot

# Инициализация Git (если еще не сделано)
git init

# Создание .gitignore (если еще нет)
cat > .gitignore << EOF
venv/
__pycache__/
*.pyc
*.db
*.log
.env
config_local.py
EOF

# Коммит файлов
git add .
git commit -m "Initial commit"

# Создание репозитория на GitHub/GitLab (опционально)
# Или используйте прямое копирование (Вариант B)
```

#### 4.2. На сервере

```bash
# Клонирование репозитория (если используете Git)
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ> telegram-bot
cd telegram-bot

# Или создайте директорию и скопируйте файлы вручную
mkdir -p ~/telegram-bot
cd ~/telegram-bot
```

### Вариант B: Прямое копирование через SCP

На вашем локальном компьютере:

```bash
# Копирование всех файлов проекта
scp -i /path/to/private_key.key -r /Users/valentin/Cancellary_Bot/* ubuntu@<PUBLIC_IP>:~/telegram-bot/
```

## Шаг 5: Настройка бота на сервере

### 5.1. Переход в директорию проекта

```bash
cd ~/telegram-bot
```

### 5.2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
```

### 5.3. Установка зависимостей

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5.4. Настройка конфигурации

```bash
# Редактирование config.py
nano config.py
```

Убедитесь, что:
- `BOT_TOKEN` установлен правильно (или через переменную окружения)
- `ADMIN_IDS` содержит правильные ID администраторов

**Безопасность**: Рекомендуется использовать переменные окружения:

```bash
# Создание файла .env (опционально)
nano .env
```

Добавьте:
```
BOT_TOKEN=ваш_токен_здесь
```

Затем установите переменную окружения:
```bash
export BOT_TOKEN="ваш_токен_здесь"
```

### 5.5. Импорт данных (если нужно)

```bash
# Если у вас есть файл data/priests_odess.xlsx
python3 reset_and_import_legacy.py
```

## Шаг 6: Настройка systemd для автозапуска

### 6.1. Создание systemd service файла

```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте следующее содержимое:

```ini
[Unit]
Description=Telegram Bot for Odessa Eparchy
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-bot
Environment="PATH=/home/ubuntu/telegram-bot/venv/bin"
Environment="BOT_TOKEN=ваш_токен_здесь"
ExecStart=/home/ubuntu/telegram-bot/venv/bin/python3 /home/ubuntu/telegram-bot/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Важно**: Замените:
- `User=ubuntu` на вашего пользователя
- `/home/ubuntu/telegram-bot` на реальный путь к проекту
- `BOT_TOKEN=...` на ваш токен (или уберите, если используете config.py)

### 6.2. Активация и запуск сервиса

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Включение автозапуска при загрузке системы
sudo systemctl enable telegram-bot

# Запуск бота
sudo systemctl start telegram-bot

# Проверка статуса
sudo systemctl status telegram-bot
```

### 6.3. Просмотр логов

```bash
# Просмотр логов в реальном времени
sudo journalctl -u telegram-bot -f

# Последние 100 строк логов
sudo journalctl -u telegram-bot -n 100
```

## Шаг 7: Настройка файрвола (если нужно)

Oracle Cloud обычно настраивает файрвол автоматически, но если нужно:

```bash
# Проверка статуса UFW
sudo ufw status

# Разрешение SSH (если еще не разрешено)
sudo ufw allow 22/tcp

# Включение файрвола
sudo ufw enable
```

## Шаг 8: Настройка резервного копирования

### 8.1. Создание скрипта резервного копирования

```bash
nano ~/backup_bot.sh
```

Добавьте:

```bash
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# Резервная копия базы данных
cp /home/ubuntu/telegram-bot/database.db $BACKUP_DIR/database_$DATE.db

# Резервная копия конфигурации
cp /home/ubuntu/telegram-bot/config.py $BACKUP_DIR/config_$DATE.py

# Удаление старых резервных копий (старше 7 дней)
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.py" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
chmod +x ~/backup_bot.sh
```

### 8.2. Настройка cron для автоматического резервного копирования

```bash
crontab -e
```

Добавьте строку (резервное копирование каждый день в 3:00):

```
0 3 * * * /home/ubuntu/backup_bot.sh >> /home/ubuntu/backup.log 2>&1
```

## Шаг 9: Мониторинг и обслуживание

### 9.1. Проверка работы бота

```bash
# Статус сервиса
sudo systemctl status telegram-bot

# Логи
sudo journalctl -u telegram-bot -f

# Проверка использования ресурсов
htop
# или
top
```

### 9.2. Перезапуск бота

```bash
sudo systemctl restart telegram-bot
```

### 9.3. Остановка бота

```bash
sudo systemctl stop telegram-bot
```

### 9.4. Обновление бота

```bash
cd ~/telegram-bot

# Если используете Git
git pull

# Активация виртуального окружения
source venv/bin/activate

# Обновление зависимостей (если нужно)
pip install -r requirements.txt

# Перезапуск сервиса
sudo systemctl restart telegram-bot
```

## Шаг 10: Безопасность

### 10.1. Обновление системы

```bash
sudo apt update && sudo apt upgrade -y
```

### 10.2. Настройка SSH ключей (отключение паролей)

```bash
sudo nano /etc/ssh/sshd_config
```

Убедитесь, что:
```
PasswordAuthentication no
PubkeyAuthentication yes
```

Перезапуск SSH:
```bash
sudo systemctl restart sshd
```

### 10.3. Регулярные обновления

Настройте автоматические обновления безопасности:

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure -plow unattended-upgrades
```

## Устранение неполадок

### Бот не запускается

1. Проверьте логи:
   ```bash
   sudo journalctl -u telegram-bot -n 50
   ```

2. Проверьте токен:
   ```bash
   sudo systemctl show telegram-bot | grep BOT_TOKEN
   ```

3. Проверьте права доступа:
   ```bash
   ls -la /home/ubuntu/telegram-bot/
   ```

### Бот падает

1. Проверьте логи на ошибки
2. Убедитесь, что база данных доступна для записи
3. Проверьте интернет-соединение сервера

### Не могу подключиться по SSH

1. Проверьте Security List в Oracle Cloud Console:
   - Compute → Instances → ваша VM → Security List
   - Убедитесь, что порт 22 открыт для вашего IP

2. Проверьте правильность IP адреса

## Дополнительные рекомендации

1. **Мониторинг**: Рассмотрите использование мониторинга (например, UptimeRobot) для отслеживания доступности бота

2. **Логирование**: Логи автоматически сохраняются в systemd journal. Для долгосрочного хранения настройте ротацию логов

3. **Масштабирование**: Если бот будет использоваться большим количеством пользователей, рассмотрите использование более мощного instance

4. **Резервное копирование**: Настройте автоматическое резервное копирование базы данных в облачное хранилище Oracle

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи: `sudo journalctl -u telegram-bot -f`
2. Проверьте документацию Oracle Cloud: https://docs.oracle.com/en-us/iaas/Content/home.htm
3. Проверьте документацию python-telegram-bot: https://python-telegram-bot.org/

## Заключение

После выполнения всех шагов ваш бот будет работать 24/7 на сервере Oracle Cloud. Бот автоматически перезапустится при перезагрузке сервера и при сбоях благодаря systemd.
