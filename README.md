[//]: # (tg-photo-bot)

[//]: # (Telegram Bot do obrobki zdjęć z DALL-E)

[//]: # (Uruchomienie)

[//]: # (make up)

[//]: # (Komponenty)

[//]: # (Bot Service – Telegram bot &#40;python-telegram-bot&#41;)

[//]: # (Image Service – FastAPI serwis obrobki &#40;OpenAI DALL-E&#41;)

[//]: # (Redis – Pub/Sub i cache)

[//]: # (User State Service – zarządzanie stanem użytkownika)

[//]: # (Funkcjonalność)

[//]: # (Wysyłanie zdjęć przez Telegram)

[//]: # (Obróbka zdjęć przez DALL-E &#40;enhance / expand&#41;)

[//]: # (Wybór rozmiaru obrazu: 256x256, 512x512, 1024x1024)

[//]: # (Zwrot przetworzonego zdjęcia do użytkownika)

[//]: # (Protokoły komunikacyjne)

[//]: # (REST API)

[//]: # (POST /process – obróbka zdjęcia)

[//]: # (POST /auth/login – pobranie JWT tokena)

[//]: # (GET /health – status serwisu)

[//]: # (WebSocket)

[//]: # (ws://image_service:8001/ws – powiadomienia w czasie rzeczywistym)

[//]: # (Redis Pub/Sub)

[//]: # (Kanał: photo_channel – powiadomienia o gotowości obrazu)

[//]: # (Bezpieczeństwo)

[//]: # (JWT autentykacja na wszystkich endpointach)

[//]: # (Nagłówek: Authorization: Bearer <JWT_TOKEN>)

[//]: # (Dane testowe:)

[//]: # (użytkownik: user)

[//]: # (hasło: password)

[//]: # (Konfiguracja &#40;.env&#41;)

[//]: # (BOT_TOKEN=twój_telegram_token)

[//]: # (OPENAI_API_KEY=twój_openai_key)

[//]: # (JWT_USERNAME=user)

[//]: # (JWT_PASSWORD=password)

[//]: # (JWT_SECRET_KEY=secret-key)

[//]: # (Technologie)

[//]: # (Python 3.11)

[//]: # (FastAPI)

[//]: # (Telegram Bot API)

[//]: # (OpenAI DALL-E)

[//]: # (Redis)

[//]: # (Docker)

[//]: # (CLI Client)

[//]: # (docker compose run --rm cli_service python cli.py)

[//]: # (Status)

[//]: # (Wszystkie serwisy uruchomione i działające)