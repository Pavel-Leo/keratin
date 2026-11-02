# Keratin-site

[![CI](https://github.com/Pavel-Leo/keratin/actions/workflows/ci.yml/badge.svg)](https://github.com/Pavel-Leo/keratin/actions/workflows/ci.yml)

Многостраничный сайт для мастера по кератиновому выпрямлению волос
(Казань). Сайт сделан под реального заказчика.
Домен для публикации: keratin-kazan.ru.

## Возможности

- Главная страница-лендинг: предложение и запись, преимущества,
  результаты с фильтром фото и видео, процедуры, подбор ухода, цены,
  мастер, отзывы, частые вопросы и контакты. Отзывы появляются только
  после публикации настоящих отзывов в админке.
- Страницы процедур, статьи с советами по уходу и прайс редактируются
  в админке, в том числе с телефона. Тексты набираются в визуальном
  редакторе, HTML очищается на сервере, пустые абзацы и лишние переносы
  убираются, после предлогов ставятся неразрывные пробелы.
- Загруженные фото перекодируются в WebP: уменьшаются, теряют EXIF
  с геометкой и получают случайное имя. Для сетки портфолио
  автоматически делаются превью, картинки грузятся по мере прокрутки.
- Ролики портфолио загружаются в админке прямо с телефона. Отдельный
  процесс перекодирует их через ffmpeg в MP4 для браузеров (до 1280 px,
  30 кадров в секунду, без метаданных и геометки), делает обложку и
  переводит HDR с iPhone в обычный цвет. Исходники хранятся вне
  публичной папки и по ссылке не отдаются. Файл проверяется до
  декодирования: принимаются только MP4, MOV и WebM, ffmpeg читает
  только локальный файл, поэтому плейлист, переименованный в `.mp4`,
  не сработает.
- Онлайн-запись через BookNow: страница записи открывается в окне
  поверх сайта, без подключения стороннего скрипта.
- Для поисковиков: sitemap.xml, robots.txt, канонические адреса,
  разметка салона по schema.org (HairSalon), превью ссылок для соцсетей
  и мессенджеров (Open Graph).
- Картинки оформления в WebP, страницы и статика отдаются сжатыми,
  шрифты загружаются с самого сайта, без запросов к Google Fonts.
- Адаптивная вёрстка для телефонов и планшетов.
- Своя страница 404.
- Защищённая админка: адрес задаётся в настройках, вход по логину
  и паролю, блокировка после неудачных попыток входа, строгая политика
  Content-Security-Policy.

## Технологии

- Python 3.12, Django 5.2 LTS
- PostgreSQL (локально можно SQLite)
- Docker Compose: nginx, gunicorn, обработчик роликов, PostgreSQL
- GitHub Actions: ruff, pytest с покрытием, pip-audit, сборка
  и проверка контейнеров
- HTML5, CSS3, Bootstrap 3
- JavaScript, jQuery (fancyBox, WOW.js)
- ffmpeg для перекодирования роликов

## Структура

```
deploy/               # nginx, резервные копии, сертификат, диагностика сервера
keratin/
├── keratin/          # настройки проекта
├── core/             # общее: админка, защита входа, 404, healthz
├── studio/           # услуги, статьи, прайс, портфолио: модели, админка, страницы
│   └── initial_content/  # начальные тексты, фото, ролики и цены
├── templates/
│   ├── base.html     # общий каркас: <head>, меню, контакты, подвал, скрипты
│   ├── core/         # страницы 404 и блокировки входа
│   └── studio/       # шаблоны страниц и общие блоки (includes/)
├── static/           # стили, скрипты, шрифты, изображения
└── tests/            # тесты pytest
```

Все страницы наследуются от `base.html` (`{% extends %}`), меню, контакты,
подвал и окно записи вынесены в `templates/studio/includes/`. Встроенных
скриптов в шаблонах нет, весь JavaScript лежит в `static/js/`.

## Локальный запуск через Docker

Нужны Git и запущенный Docker с Compose v2 (на Windows и macOS:
Docker Desktop в режиме Linux-контейнеров). Python и PostgreSQL
на компьютер устанавливать не нужно. Команды подходят для PowerShell
и Bash.

### 1. Скачать проект

```bash
git clone https://github.com/Pavel-Leo/keratin.git
cd keratin
```

Если проект уже скачан, откройте терминал в корне репозитория.

### 2. Собрать и запустить

```bash
docker compose -f docker-compose.dev.yml up -d --build --wait
```

Локальные настройки уже заданы в `docker-compose.dev.yml`, создавать
`.env` не нужно. Запускаются Django, PostgreSQL и обработчик роликов
с ffmpeg. Миграции применяются автоматически.

Сайт: http://127.0.0.1:8000/.

### 3. Загрузить содержимое и создать администратора

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py load_initial_content
docker compose -f docker-compose.dev.yml exec web python manage.py createsuperuser
```

Админка: http://127.0.0.1:8000/admin/.
`load_initial_content` можно запускать повторно: существующие записи
сохраняются. Начальные ролики обрабатываются в фоне.

### Работа с проектом

Исходники подключены из папки `keratin/`: изменения Python автоматически
перезапускают сервер разработки, изменения шаблонов и стилей видны
после обновления страницы. После изменения кода обработчика роликов
перезапустите его:

```bash
docker compose -f docker-compose.dev.yml restart worker
```

После изменения зависимостей повторите запуск с `--build`.
После добавления миграций выполните:

```bash
docker compose -f docker-compose.dev.yml exec web python manage.py migrate
```

Журналы и остановка:

```bash
docker compose -f docker-compose.dev.yml logs -f web worker
docker compose -f docker-compose.dev.yml down
```

База и загруженные файлы сохраняются в Docker volumes между запусками.
Команда `down -v` удаляет эти данные. Локальный проект Compose называется
`keratin-dev`, его тома отделены от серверного проекта `keratin`.

Публикация на сервере описана отдельно в [DEPLOY.md](DEPLOY.md).

## Локальный запуск без Docker

Клонировать репозиторий и перейти в него:

```bash
git clone https://github.com/Pavel-Leo/keratin.git
cd keratin
```

Создать и активировать виртуальное окружение:

```bash
python -m venv venv
source venv/bin/activate        # Linux и macOS
source venv/Scripts/activate    # Windows (Git Bash)
```

Установить зависимости:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Запустить сервер разработки из папки с `manage.py`:

```bash
cd keratin
DEBUG=True python manage.py runserver
```

В PowerShell:

```powershell
cd keratin
$env:DEBUG = "True"; python manage.py runserver
```

Сайт откроется по адресу http://127.0.0.1:8000/.

`DEBUG=True` нужен для локального запуска: без него Django не отдаёт
статические файлы, и сайт откроется без стилей и картинок.

Создать базу, загрузить начальное наполнение и пользователя для админки:

```bash
DEBUG=True python manage.py migrate
DEBUG=True python manage.py load_initial_content
DEBUG=True python manage.py createsuperuser
```

`load_initial_content` добавляет только то, чего ещё нет в базе, и не
трогает отредактированные записи, поэтому её можно запускать повторно.

Локально админка открывается по адресу http://127.0.0.1:8000/admin/ и
пускает по логину и паролю.

## Ролики портфолио

Загруженный в админке ролик встаёт в очередь и появляется на сайте после
перекодирования. Очередь разбирает команда, которой нужны `ffmpeg` и
`ffprobe` (на Debian и Ubuntu ставятся пакетом `ffmpeg`):

```bash
DEBUG=True python manage.py process_videos          # обработать очередь и выйти
DEBUG=True python manage.py process_videos --watch  # работать постоянно
```

Состояние каждого ролика видно в админке: «Ждёт обработки»,
«Обрабатывается», «Готов» или «Ошибка» с причиной. Действие
«Перекодировать заново» снова ставит выбранные ролики в очередь.

## Проверки

Установить зависимости разработки и выполнить проверки:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check .
python -m pytest -q
```

Начальное наполнение добавляется командой `load_initial_content`.
Тексты первого экрана, преимущества, информация о мастере, вопросы,
отзывы и контакты редактируются в админке. У фото и роликов можно выбрать
процедуру для фильтра портфолио. Цена и скидка в начальном наполнении
должны соответствовать действующим условиям студии.

## Переменные окружения

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `SECRET_KEY` | секретный ключ Django | обязателен при `DEBUG=False` |
| `DEBUG` | режим отладки | `False` |
| `ALLOWED_HOSTS` | разрешённые хосты через запятую | `localhost,127.0.0.1` |
| `CSRF_TRUSTED_ORIGINS` | адреса сайта с протоколом через запятую | пусто |
| `ADMIN_URL` | адрес админки | `admin/` |
| `USE_X_REAL_IP` | брать адрес клиента из заголовка nginx | `False` |
| `AXES_FAILURE_LIMIT` | неудачных попыток входа до блокировки | `5` |
| `AXES_COOLOFF_HOURS` | на сколько часов блокируется адрес | `1` |
| `BOOKING_URL` | страница онлайн-записи BookNow | адрес студии |
| `MEDIA_ROOT` | папка загруженных фото и готовых роликов | `keratin/media` |
| `PRIVATE_MEDIA_ROOT` | папка исходников роликов, не раздаётся | `keratin/private_media` |
| `FILE_UPLOAD_TEMP_DIR` | куда временно пишутся большие загрузки | системная |
| `FFMPEG_BINARY`, `FFPROBE_BINARY` | пути к ffmpeg и ffprobe | из `PATH` |
| `VIDEO_MAX_UPLOAD_MB` | наибольший размер загружаемого ролика | `500` |
| `VIDEO_MAX_SECONDS` | наибольшая длительность ролика | `180` |
| `VIDEO_TIMEOUT_SECONDS` | сколько ждать перекодирования одного ролика | `1800` |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` | подключение к PostgreSQL; без `POSTGRES_DB` используется SQLite | |

В продакшене обязательно задать свой `SECRET_KEY`, `ALLOWED_HOSTS` и
неочевидный `ADMIN_URL`. Команда `python manage.py check --deploy`
предупредит, если админка осталась по адресу `/admin/`.

## Автор

Леонтьев Павел, [GitHub](https://github.com/Pavel-Leo)
