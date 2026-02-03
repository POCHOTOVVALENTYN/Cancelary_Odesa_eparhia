# Быстрая инструкция по развертыванию на Oracle Cloud

## Краткая версия (для опытных пользователей)

### 1. Создание VM в Oracle Cloud
- Compute → Instances → Create Instance
- Image: Ubuntu 22.04
- Shape: VM.Standard.E2.1.Micro (бесплатный tier)
- Сохраните приватный ключ SSH

### 2. Подключение к серверу
```bash
ssh -i private_key.key ubuntu@<PUBLIC_IP>
```

### 3. Установка зависимостей
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv git -y
```

### 4. Загрузка проекта
```bash
# Вариант 1: Через SCP (с локального компьютера)
scp -i private_key.key -r /Users/valentin/Cancellary_Bot/* ubuntu@<PUBLIC_IP>:~/telegram-bot/

# Вариант 2: Через Git
git clone <ваш_репозиторий> ~/telegram-bot
```

### 5. Настройка бота
```bash
cd ~/telegram-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настройте токен в config.py или через переменную окружения
export BOT_TOKEN="ваш_токен"
```

### 6. Создание systemd service
```bash
sudo nano /etc/systemd/system/telegram-bot.service
```

Вставьте:
```ini
[Unit]
Description=Telegram Bot for Odessa Eparchy
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/telegram-bot
Environment="PATH=/home/ubuntu/telegram-bot/venv/bin"
Environment="BOT_TOKEN=ваш_токен"
ExecStart=/home/ubuntu/telegram-bot/venv/bin/python3 /home/ubuntu/telegram-bot/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 7. Запуск
```bash
sudo systemctl daemon-reload
sudo systemctl enable telegram-bot
sudo systemctl start telegram-bot
sudo systemctl status telegram-bot
```

### 8. Просмотр логов
```bash
sudo journalctl -u telegram-bot -f
```

## Полезные команды

```bash
# Перезапуск бота
sudo systemctl restart telegram-bot

# Остановка бота
sudo systemctl stop telegram-bot

# Просмотр статуса
sudo systemctl status telegram-bot

# Последние логи
sudo journalctl -u telegram-bot -n 50
```

## Важные замечания

1. **Безопасность**: Используйте переменные окружения для токена, не храните его в config.py в Git
2. **Резервное копирование**: Настройте автоматическое резервное копирование базы данных
3. **Мониторинг**: Проверяйте логи регулярно для выявления проблем

Подробная инструкция: см. файл `РАЗВЕРТЫВАНИЕ_ORACLE_CLOUD.md`
