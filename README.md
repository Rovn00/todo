# Список задач

Простой учебный проект для базового уровня DevOps-задания (уровень 1).
Можно добавить задачу и удалить её. Задачи сохраняются в SQLite.
HTML, CSS и JavaScript находятся в одном index.html, сервер — в app.py.
Используются Python 3.13, Flask, SQLite, Docker, Compose и GitHub Actions.
SQLite — база в файле, поэтому отдельный сервер БД не нужен.
Внешний сервис БД в задании желателен, но для уровня 1 не обязателен.
Уровни 2 и 3 (Kubernetes, Grafana и дополнительные инструменты) здесь не реализованы.

## Запуск через Compose

Нужны Docker с запущенным движком и Docker Compose.
Из папки проекта:

```bash
cp .env.example .env
docker compose up -d --build
```

Открыть http://localhost:8000. Все компоненты запускаются одной командой.

Проверка и логи:

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/api/items
docker compose ps
docker compose logs app
```

/health возвращает {"status":"ok"}, если сервер и база работают.
В браузере добавить задачу, обновить страницу, затем удалить задачу.

Остановка:

```bash
docker compose down
```

Задачи остаются в Docker volume. `docker compose down -v` удаляет также все задачи.

## Docker без Compose

```bash
docker build -t todo .
docker run -d --name todo -p 8000:8000 -e PORT=8000 -e DB_PATH=/data/tasks.db -v todo-data:/data todo
curl --fail http://localhost:8000/health
docker logs todo
docker stop todo
docker rm todo
```

## Запуск без Docker

Нужен Python 3.10 или новее.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Открыть http://localhost:8000. Остановка — Ctrl+C.
Для простоты используется встроенный сервер Flask, предназначенный для учебного и локального запуска.

## Переменные окружения

| Переменная | Значение по умолчанию | Назначение |
| --- | --- | --- |
| PORT | 8000 | Порт сервера; в .env для Compose — внешний порт компьютера |
| DB_PATH | data/tasks.db | Путь к файлу SQLite при локальном запуске |

В контейнере PORT=8000 и DB_PATH=/data/tasks.db задаются конфигурацией.
Файл .env используется Compose автоматически. При запуске `python app.py` переменные надо передать самому:

```bash
PORT=8080 DB_PATH=data/other.db python app.py
```

Для изменения внешнего порта Compose поставить PORT=8080 в .env и выполнить:

```bash
docker compose up -d
curl --fail http://localhost:8080/health
```

Пароли и токены не нужны. .env и файлы базы исключены из Git.
Не добавлять настоящие секреты в конфигурацию или README.

## Проверки и CI

```bash
python -m unittest -v
```

Тесты проверяют страницу, добавление, чтение и удаление задач, неправильный ввод,
сохранение в SQLite, недоступность базы и восстановление. Используется временная база.
GitHub Actions после push или pull request получает код, устанавливает Flask,
запускает тесты, собирает Docker image и проверяет /health запущенного контейнера.
Можно запустить CI вручную через Actions → CI → Run workflow.

Чтобы появилась настоящая история CI, создать пустой репозиторий на GitHub,
подставить его адрес и отправить проект:

```bash
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

Результат показать преподавателю во вкладке Actions этого репозитория.
Пока проект не отправлен на GitHub, истории запусков CI нет.

## Что показать на проверке уровня 1

1. `docker compose up -d --build` — сборка и запуск.
2. Добавить задачу в браузере, выполнить `docker compose restart`, показать сохранённую задачу.
3. Изменить PORT в .env и открыть приложение на новом порту.
4. Сделать изменение кода, commit и push, показать успешный CI в Actions.
5. `docker compose logs app` — показать запросы в логах.
6. `docker compose stop app` — приложение недоступно; `docker compose start app` — снова работает.
7. `docker compose down` — остановить и удалить контейнер.

Для промежуточной проверки рассказать: что добавил, что работает, какая возникла
проблема, как исправил и какой командой проверил. Файлы конфигурации сами по себе
не заменяют демонстрацию запуска. Проверки Pod, метрик Grafana и подключения
к внешней БД относятся к дополнительным уровням и этим проектом не покрываются.

## Коротко об инструментах

Image — образ с Python, зависимостями и кодом. Container — запущенный экземпляр образа.
Dockerfile описывает сборку образа. `-p 8000:8000` связывает порт компьютера с портом контейнера.
Переменные окружения позволяют менять настройки без редактирования кода.
Compose описывает запуск и постоянный volume для базы.
CI автоматически проверяет изменения и сборку. Deployment в этом уровне выполняется
вручную командой `docker compose up -d --build` после обновления кода.
