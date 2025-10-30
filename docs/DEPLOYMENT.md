```
# 🚀 Руководство по деплою (Deployment Guide)

Пошаговая инструкция по развёртыванию **RAG Production Platform** на собственном VPS-сервере.

---

## 🧩 Предварительные требования

- VPS с **2 ГБ RAM**, **2 vCPU**, **30 ГБ** хранилища  
- ОС **Ubuntu 20.04+** или **Debian 11+**  
- Доступ **root** или **sudo**  
- (опционально) Зарегистрированный домен — для настройки HTTPS

---

## ⚙️ Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка версий
docker --version
docker-compose --version
````

---

## 📥 Шаг 2: Клонирование репозитория

```bash
cd ~
git clone https://github.com/yourusername/rag-production-platform.git
cd rag-production-platform
```

---

## 🧾 Шаг 3: Настройка окружения

```bash
# Копируем шаблон
cp .env.example .env

# Редактируем переменные окружения
nano .env
```

**Необходимые переменные:**

```bash
LLAMAPARSE_API_KEY=ваш_ключ
YANDEX_API_KEY=ваш_ключ
YANDEX_FOLDER_ID=ваш_folder_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=ваш_ключ
```

---

## 🏗️ Шаг 4: Развёртывание сервисов

```bash
# Сборка всех контейнеров (занимает 5–10 минут)
docker-compose build

# Запуск
docker-compose up -d

# Проверка статуса
docker-compose ps
```

**Ожидаемый результат:**

```
NAME              STATUS          PORTS
rag_validation    Up (healthy)    0.0.0.0:8001->8001/tcp
rag_parser        Up (healthy)    0.0.0.0:8002->8002/tcp
rag_embedder      Up (healthy)    0.0.0.0:8003->8003/tcp
rag_storage       Up (healthy)    0.0.0.0:8004->8004/tcp
rag_nginx         Up (healthy)    0.0.0.0:8080->80/tcp
rag_redis         Up (healthy)    6379/tcp
rag_prometheus    Up              0.0.0.0:9090->9090/tcp
```

---

## 🔍 Шаг 5: Проверка развёртывания

```bash
# Проверка состояния
curl http://localhost:8080/health

# Проверка валидации
curl -X POST http://localhost:8080/api/validation/validate \
  -H "Content-Type: application/json" \
  -d '{"file_id":"test","file_name":"test.pdf","file_type":"application/pdf","file_size_bytes":1000000}'

# Проверка Embedder-сервиса
curl http://localhost:8080/api/embedder/test
```

---

## 🔐 Шаг 6: Настройка файрвола

```bash
# Разрешаем SSH
sudo ufw allow 22/tcp

# Разрешаем доступ к Nginx
sudo ufw allow 8080/tcp

# Включаем файрвол
sudo ufw --force enable
```

---

## 📊 Шаг 7: Настройка мониторинга

**Доступ к Prometheus:**

```
http://YOUR_SERVER_IP:9090
```

**Проверка состояния сервисов:**

* Перейдите во вкладку **Status → Targets**
* Убедитесь, что все статусы отображаются как **UP**

---

## 🧯 Решение возможных проблем

### ❗ Сервисы не запускаются

```bash
# Проверить логи
docker-compose logs -f [имя_сервиса]

# Перезапустить конкретный сервис
docker-compose restart [имя_сервиса]
```

###  Не хватает памяти

```bash
# Создать swap-файл
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### ⚔️ Конфликт портов

```bash
# Проверить, что использует порт
sudo lsof -i :8080

# Завершить процесс
sudo kill -9 [PID]
```

---

## 🧩 Обслуживание и обновления

### 🔄 Обновление сервисов

```bash
cd ~/rag-production-platform
git pull
docker-compose build
docker-compose up -d
```

### 📜 Просмотр логов

```bash
docker-compose logs -f
```

### 💾 Резервное копирование

```bash
# Создание архива с конфигурацией
tar -czf backup-$(date +%Y%m%d).tar.gz .env docker-compose.yml

# Скачивание на локальный компьютер
scp user@server:~/rag-production-platform/backup-*.tar.gz ./
```

---

## 🚀 Следующие шаги

* Настройте **n8n workflow** с указанием IP вашего сервера
* Настройте HTTPS через **Let’s Encrypt (опционально)**
* Добавьте **Grafana dashboards** для визуализации метрик
* Настройте **CI/CD pipeline** для автоматических обновлений

---

📄 **Готово!**
После выполнения этих шагов все микросервисы платформы будут развернуты и готовы к интеграции с n8n и AI-агентом.

```
