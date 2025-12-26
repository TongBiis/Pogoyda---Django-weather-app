## Pogoyda - Weather Forecast Web Application ##

![Django](https://img.shields.io/badge/Django-5.2-green)
![Python](https://img.shields.io/badge/Python-3.14-blue)
![Tests](https://img.shields.io/badge/Tests-100%25%20passing-brightgreen)
![Docker](https://img.shields.io/badge/Docker-Ready-blue)

A Django-based weather forecast application with user authentication, multi-language support, and smart caching.

## Key Features

- Weather Forecast: Real-time weather data and 2-day forecast for any city
- Custom User Model: Session authentication with JWT email verification
- Password Recovery: Secure password reset vith JWT tokens
- Caching: Redis-based caching to optimize API calls (weather data cached for 60s)
- Multi-language: English/Russian support with automatic browser language detection
- Russian Morphology: Proper case declension using pymorphy3 (e.g., "в Москве" instead of "в Москва")
- Favorites & History: Save favorite cities and track search history
- Rate Limiting: Protection against abuse with configurable limits per endpoint
- IP Geolocation: Auto-detection of user location via IP address

## Tech Stack

- Django 5.2 - Web framework
- Redis - Caching backend
- PostgreSQL/SQLite3 - Database
- PyJWT - Token-based authentication
- pymorphy3 - Russian morphological analysis
- django-ratelimit - Rate limiting middleware
- WeatherAPI.com - Weather data provider
- IPInfo.io - IP geolocation service

## Quick Start

**Recommended variant**
↓          ↓          ↓
1. Clone the repository
2. docker-compose up
3. Open http://localhost:8000


**Optional variant**
↓         ↓        ↓
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up `.env` file with required variables (see settings.py)
4. Run Redis server
5. Run migrations: `python manage.py migrate`
6. Start server: `python manage.py runserver`

## Deployment

The project is deployed and publicly available at https://pogoyda.ru.

Production environment setup:
- Server: Ubuntu VPS (Virtual Private Server)
- Application Server: Gunicorn with systemd service management
- Web Server: Nginx as reverse proxy and static files handler
- Database: PostgreSQL (installed and configured directly on the VPS)
- Caching: Redis (installed as a system service)
- Domain & SSL: Domain configuration with Regru and confirmed SSL certificate

## Testing

The project includes comprehensive test coverage for:
- User authentication and registration flow
- Weather data and caching
- Russian language morphology processing
- Rate limiting functionality
- Form validation and error handling

Run tests: `python manage.py test`

## For a quick start, a `.env` file with test API keys and gmail account(for SMTP) has already been prepared. ##
