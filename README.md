# tg-photo-bot

# Telegram Bot do obrobki zdjęć z DALL-E

## Uruchomienie

```bash
make up
```

## Komponenty

1. **Bot Service** - Telegram bot (python-telegram-bot)
2. **Image Service** - FastAPI serwis obrobki (OpenAI DALL-E)
3. **Redis** - Pub/Sub i cache
4. **User State Service** - Zarządzanie stanem

## Funkcjonalność

- ✅ Wysyłanie zdjęć przez Telegram
- ✅ Obrobka przez DALL-E (enhance/expand)
- ✅ Wybór rozmiaru (256x256, 512x512, 1024x1024)
- ✅ Zwrot przetworzonego zdjęcia

## Protokoły Komunikacyjne

### REST API
- POST /process - Obrobka zdjęcia
- POST /auth/login - Pobranie JWT tokena
- GET /health - Status serwisu

### WebSocket
- ws://image_service:8001/ws - Real-time powiadomienia

### Redis Pub/Sub
- Kanał: photo_channel - Powiadomienia o gotowości

## Bezpieczeństwo

- JWT autentykacja na wszystkich endpoints
- Token: Bearer <JWT_TOKEN>
- Użytkownik: user, Hasło: password

## Konfiguracja (.env)

```
BOT_TOKEN=twój_telegram_token
OPENAI_API_KEY=twój_openai_key
JWT_USERNAME=user
JWT_PASSWORD=password
JWT_SECRET_KEY=secret-key
```

## Technologie

- Python 3.11
- FastAPI
- Telegram Bot API
- OpenAI DALL-E
- Redis
- Docker

## CLI Client

```bash
docker compose run --rm cli_service python cli.py
```

## Status

Wszystkie serwisy uruchomione i działające ✅