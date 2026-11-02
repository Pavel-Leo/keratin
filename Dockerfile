# syntax=docker/dockerfile:1

# Общая основа: Python и непривилегированный пользователь.
FROM python:3.12-slim-trixie AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app \
       --shell /usr/sbin/nologin app
WORKDIR /app

# Зависимости ставятся в отдельное окружение и копируются в итоговый образ.
FROM base AS deps
COPY requirements.txt .
RUN python -m venv /venv && /venv/bin/pip install -r requirements.txt

# Сайт: gunicorn за nginx.
FROM base AS web
ENV PATH=/venv/bin:$PATH \
    DJANGO_SETTINGS_MODULE=keratin.settings
COPY --from=deps /venv /venv
COPY keratin/ /app/
# Ключ нужен только чтобы загрузить настройки при сборке статики.
RUN SECRET_KEY=collectstatic-only python manage.py collectstatic --noinput \
    && mkdir -p /app/media /app/private_media/tmp \
    && chown app:app /app/media /app/private_media /app/private_media/tmp
USER app
EXPOSE 8000
CMD ["gunicorn", "keratin.wsgi", "--bind", "0.0.0.0:8000"]

# Обработчик роликов: тот же код и ffmpeg.
FROM web AS worker
USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
USER app
CMD ["python", "manage.py", "process_videos", "--watch"]
