# 🎙️ Voice Transcription Service

**Сервис автоматической транскрибации аудио** с разбивкой по спикерам. Принимает аудиофайлы через API, отправляет на распознавание в Soniox, сохраняет готовый текст в PostgreSQL.

> 📘 Подробный разбор кейса и архитектуры — [на сайте портфолио](https://aimentorcrm.com/portfolio/voice-recorder-transcript/).

---

## Как это работает

### Полный цикл обработки

```
1. Клиент отправляет аудиофайл → POST /webhook/upload
   └─ Файл может быть передан как URL (url) или как Base64 (base64)
   └─ Поддерживаемые форматы: MP3, WAV, FLAC, OGG, M4A (audio/mpeg, audio/wav, etc.)

2. Сервис проверяет лимиты пользователя
   └─ Если userId передан: проверка TRANSCRIPTION_LIMIT (по умолчанию 5)
   └─ Email'ы из LIMIT_EXEMPT_EMAILS пропускаются без ограничений
   └─ При превышении лимита: возвращается ошибка limit_exceeded

3. Сервис отправляет файл в Soniox API
   └─ Модель: stt-async-preview-v1 (асинхронная)
   └─ Включена диаризация спикеров (enable_speaker_diarization)
   └─ Включена разбивка на параграфы (enable_paragraphs)
   └─ Указан webhook_url для обратного вызова

4. Soniox обрабатывает аудио (от 5 секунд до нескольких минут)
   └─ Распознаёт речь
   └─ Определяет спикеров
   └─ Отправляет результат на callback URL сервиса

5. Сервис получает результат → POST /webhook/soniox-callback/{filename}
   └─ Парсит токены (слова) от Soniox
   └─ Группирует токены по спикерам
   └─ Формирует диалог с временными метками
   └─ Сохраняет полный текст в PostgreSQL (таблица transcriptions)

6. Проверка лимитов после сохранения
   └─ Если пользователь достиг лимита → деактивация (is_approved = false)
   └─ Если настроен SMTP → отправка email-уведомления администратору
```

### Формат результата

```json
{
  "dialog": [
    {
      "speaker": "Speaker_1",
      "text": "Добрый день, это Иван.",
      "start_time": "0:00",
      "end_time": "0:03"
    },
    {
      "speaker": "Speaker_2",
      "text": "Здравствуйте, Иван. Слушаю вас.",
      "start_time": "0:04",
      "end_time": "0:07"
    }
  ],
  "full_text": "[Speaker_1] Добрый день, это Иван.\n[Speaker_2] Здравствуйте, Иван. Слушаю вас.",
  "total_replicas": 2
}
```

---

## API

### Загрузка аудио на транскрибацию

```http
POST /webhook/upload
Content-Type: application/json

{
  "filename": "call_2026.mp3",
  "url": "https://storage.example.com/audio/call.mp3",
  "base64": "",
  "userId": 42,
  "mimeType": "audio/mpeg",
  "duration": 120.5,
  "source": "voice-recorder"
}
```

| Поле | Тип | Обязательное | Описание |
|------|-----|-------------|----------|
| `filename` | string | Да | Название файла |
| `url` | string | Нет* | URL аудиофайла |
| `base64` | string | Нет* | Аудио в Base64 |
| `userId` | int | Нет | ID пользователя для учёта лимитов |
| `mimeType` | string | Нет | MIME-тип (audio/mpeg и др.) |
| `duration` | float | Нет | Длительность в секундах |
| `source` | string | Нет | Источник (voice-recorder и др.) |

*Одно из полей `url` или `base64` должно быть заполнено.

### Получение истории транскрипций

```http
GET /api/v1/transcriptions?user_id=42&limit=50
```

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|-------------|----------|
| `user_id` | int | — | Фильтр по пользователю |
| `limit` | int | 50 | Максимум записей (до 200) |

---

## Установка

### 1. Клонирование

```bash
git clone https://github.com/Ivan-Baidyk/voice-transcription.git
cd voice-transcription
```

### 2. Настройка

```bash
cp .env.example .env
nano .env  # Заполните реальными значениями
```

### 3. База данных

Создайте таблицы в PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    user_id INTEGER
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255),
    is_approved BOOLEAN DEFAULT true
);
```

### 4. Запуск

```bash
# Docker (рекомендуется)
docker compose up -d

# Или напрямую
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

### Обязательные

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `DATABASE_URL` | PostgreSQL (asyncpg) | `postgresql+asyncpg://user:pass@host:5432/db` |
| `SONIOX_API_KEY` | API-ключ Soniox | Получить на app.soniox.com |
| `SONIOX_WEBHOOK_BASE` | Публичный URL сервера | `https://transcript.yourdomain.com` |

### Лимиты

| Переменная | По умолчанию | Описание |
|-----------|-------------|----------|
| `TRANSCRIPTION_LIMIT` | 5 | Максимум транскрипций на пользователя |
| `LIMIT_EXEMPT_EMAILS` | — | Email'ы без ограничений (через запятую) |

### Email-уведомления (опционально)

| Переменная | Пример |
|-----------|--------|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | `notify@gmail.com` |
| `SMTP_PASSWORD` | App Password |
| `NOTIFICATION_EMAIL` | `admin@company.com` |

### Общие

| Переменная | По умолчанию |
|-----------|-------------|
| `TZ` | `Europe/Moscow` |
| `LOG_LEVEL` | `info` |

---

## Стек технологий

| Компонент | Технология | Зачем |
|-----------|-----------|-------|
| Веб-фреймворк | FastAPI | Асинхронный, быстрый, авто-документация |
| ASGI-сервер | Uvicorn | Запуск FastAPI в production |
| База данных | PostgreSQL + asyncpg | Асинхронные запросы, connection pool |
| Транскрибация | Soniox API | Распознавание речи + диаризация спикеров |
| HTTP-клиент | httpx | Асинхронные запросы к Soniox |
| Валидация | Pydantic v2 | Проверка входящих данных |
| Email | smtplib (stdlib) | Отправка уведомлений |
| Контейнеризация | Docker + Compose | Изолированное окружение |

---

## Результаты

- **Production-сервис, а не скрипт**: FastAPI + PostgreSQL, Docker Compose, асинхронная обработка вебхуков Soniox.
- **Диаризация спикеров** — на выходе не «простыня» текста, а реплики с разделением, кто говорил.
- **5 форматов аудио** (MP3, WAV, FLAC, OGG, M4A) и два способа передачи: URL или Base64.
- **Квоты на пользователя** (`TRANSCRIPTION_LIMIT`) и белый список email — сервис можно открывать наружу.
- **~470 строк Python** в 8 модулях: конфиг, БД, API, сервис Soniox, email-уведомления.

## Безопасность

- 🔐 Все секреты в `.env` (исключён из git через `.gitignore`)
- 🔐 `SONIOX_API_KEY` — в заголовке Authorization, never in URL
- 🔐 База данных — доступ только по паролю
- 🔐 CORS — настраивается под свой домен
- 🔐 Логи — без API-ключей и паролей

---

## Лицензия

MIT
