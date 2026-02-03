# Устранение проблем с SSH подключением к Oracle Cloud

## Проблема: Permission denied (publickey)

Эта ошибка означает, что сервер не может аутентифицировать вас по публичному ключу.

## Решения

### Решение 1: Проверка формата ключа

Oracle Cloud может требовать ключ в формате OpenSSH. Проверьте формат:

```bash
# Проверка формата ключа
head -1 /Users/valentin/Downloads/Cancelary_ssh-key.key
```

Должно начинаться с:
- `-----BEGIN OPENSSH PRIVATE KEY-----` (новый формат)
- `-----BEGIN RSA PRIVATE KEY-----` (старый формат)
- `-----BEGIN PRIVATE KEY-----` (PKCS#8)

### Решение 2: Конвертация ключа (если нужно)

Если ключ в неправильном формате:

```bash
# Конвертация в формат OpenSSH (если нужно)
ssh-keygen -p -m PEM -f /Users/valentin/Downloads/Cancelary_ssh-key.key
```

### Решение 3: Проверка прав доступа

```bash
# Установка правильных прав (только для владельца)
chmod 600 /Users/valentin/Downloads/Cancelary_ssh-key.key
```

### Решение 4: Использование правильного пользователя

В зависимости от образа Oracle Cloud, пользователь может быть:
- `ubuntu` (для Ubuntu)
- `opc` (для Oracle Linux)
- `ec2-user` (для некоторых образов)

Попробуйте:

```bash
# Для Ubuntu
ssh -i /Users/valentin/Downloads/Cancelary_ssh-key.key ubuntu@92.5.40.131

# Для Oracle Linux
ssh -i /Users/valentin/Downloads/Cancelary_ssh-key.key opc@92.5.40.131
```

### Решение 5: Проверка публичного ключа в Oracle Cloud Console

1. Зайдите в Oracle Cloud Console
2. Compute → Instances → ваша VM
3. Проверьте раздел "SSH Keys" или "Boot Volume"
4. Убедитесь, что ваш публичный ключ добавлен

### Решение 6: Добавление ключа через Console (если нужно)

Если ключ не был добавлен при создании VM:

1. В Oracle Cloud Console:
   - Compute → Instances → ваша VM
   - Нажмите "Edit"
   - В разделе "Add SSH Keys" добавьте ваш публичный ключ
   - Сохраните изменения

2. Получите публичный ключ из приватного:

```bash
# Генерация публичного ключа из приватного
ssh-keygen -y -f /Users/valentin/Downloads/Cancelary_ssh-key.key
```

Скопируйте вывод и добавьте в Oracle Cloud Console.

### Решение 7: Использование Cloud Shell (альтернатива)

Если SSH не работает, используйте Cloud Shell в Oracle Cloud Console:

1. В Oracle Cloud Console нажмите иконку "Cloud Shell" (вверху справа)
2. Подключитесь к вашей VM через Cloud Shell

### Решение 8: Проверка Security List

Убедитесь, что порт 22 открыт:

1. Oracle Cloud Console → Networking → Virtual Cloud Networks
2. Выберите вашу VCN
3. Security Lists → Default Security List
4. Ingress Rules → проверьте, что порт 22 открыт для вашего IP или 0.0.0.0/0

### Решение 9: Подробный вывод для диагностики

```bash
# Подключение с подробным выводом для диагностики
ssh -v -i /Users/valentin/Downloads/Cancelary_ssh-key.key ubuntu@92.5.40.131
```

Флаг `-v` покажет подробную информацию о процессе подключения.

### Решение 10: Создание нового ключа (если ничего не помогает)

```bash
# Генерация новой пары ключей
ssh-keygen -t rsa -b 4096 -f ~/.ssh/oracle_cloud_key -N ""

# Просмотр публичного ключа
cat ~/.ssh/oracle_cloud_key.pub
```

Затем:
1. Скопируйте публичный ключ (`oracle_cloud_key.pub`)
2. Добавьте его в Oracle Cloud Console при редактировании VM
3. Подключитесь используя приватный ключ:

```bash
ssh -i ~/.ssh/oracle_cloud_key ubuntu@92.5.40.131
```

## Проверка подключения

После успешного подключения вы должны увидеть приглашение:

```
ubuntu@instance-name:~$
```

## Следующие шаги после подключения

После успешного подключения выполните:

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install python3 python3-pip python3-venv git -y

# Проверка версии Python
python3 --version
```

## Дополнительная помощь

Если проблема сохраняется:
1. Проверьте документацию Oracle Cloud: https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/accessinginstance.htm
2. Убедитесь, что используете правильный IP адрес (Public IP)
3. Проверьте, что VM запущена (Status = Running)
