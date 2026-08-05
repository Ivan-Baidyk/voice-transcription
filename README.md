# 🎙️ Voice Transcription Service

**FastAPI-сервис для распознавания аудио в текст** с разбивкой по спикерам через Soniox API. Замена n8n workflow для транскрибации звонков и встреч.

---

## Возможности

- 📤 Приём аудиофайлов через Webhook
- 🎙️ Транскрибация с диаризацией спикеров (Soniox API)
- 💾 Сохранение результатов в PostgreSQL
- 🚫 Лимиты транскрипций на пользователя
- 📧 Email-уведомления при деактивации
- ⭐ Исключения для VIP-пользователей (без лимитов)
- 📊 API для получения истории транскрипций

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
nano .env  # заполните реальными значениями
```

### 3. База данных

Создайте таблицы в PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS transcriptions (
    id SERIAL PRIMARY KEY,
    text TEXT,
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
# Через Docker (рекомендуется)
docker compose up -d

# Или напрямую
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Переменные окружения

| Переменная | Описание | Пример |
|-----------|----------|--------|
| `DATABASE_URL` | PostgreSQL (asyncpg) | `postgresql+asyncpg://user:pass@host/db` |
| `SONIOX_API_KEY` | API-ключ Soniox | `soniox...` |
| `SONIOX_WEBHOOK_BASE` | URL для callback | `https://transcript.yourdomain.com` |
| `TRANSCRIPTION_LIMIT` | Лимит на пользователя | `5` |
| `LIMIT_EXEMPT_EMAILS` | Исключения (через запятую) | `admin@co.com,ceo@co.com` |
| `SMTP_HOST` | SMTP-сервер | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP-порт | `587` |
| `SMTP_USER` | Логин SMTP | `notify@co.com` |
| `SMTP_PASSWORD` | Пароль SMTP | `app_password` |

---

## API

### Загрузка аудио

```http
POST /webhook/upload
Content-Type: application/json

{
  "filename": "call_2026.mp3",
  "url": "https://storage.example.com/audio/call_2026.mp3",
  "userId": 42,
  "mimeType": "audio/mpeg",
  "duration": 120.5
}
```

### Получение транскрипций

```http
GET /api/v1/transcriptions?user_id=42&limit=50
```

---

## Архитектура

```
Voice Recorder (Frontend)
  │ POST /webhook/upload
  ▼
FastAPI Service
  ├─ Soniox API (transcription)
  ├─ PostgreSQL (storage)
  └─ SMTP (email notifications)
  │
  ▼ Soniox Callback
  ├─ Save transcription
  ├─ Check limits
  └─ Deactivate user if limit exceeded
```

---

## Безопасность

- Все секреты в `.env` (исключён из git)
- CORS настроен
- API-ключи не логируются
- PostgreSQL за файрволлом

---

## Лицензия

MIT
