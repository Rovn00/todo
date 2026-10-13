# Список задач и DevOps

Простое приложение: добавить задачу, посмотреть список, удалить задачу.
Один app.py и один многострочный index.html с CSS и JavaScript внутри.
Сервер — Flask + Gunicorn, база — PostgreSQL. Настройки приходят из окружения.

## Какие уровни реализованы

| Уровень | Что добавлено |
| --- | --- |
| 1 | HTTP-приложение, Git, README, Dockerfile, Compose, переменные окружения, CI |
| 2 | Kubernetes: Deployment, Service, ConfigMap, Secret, PVC; probes; Prometheus и Grafana с dashboard |
| 3 | Три выбранные дополнительные задачи: Helm Chart, Container Registry (GHCR), deployment по кнопке после CI |

Задание разрешает выбрать несколько задач для уровня 3. Loki, Terraform, Ansible,
Argo CD и уведомления не входят в выбранные задачи.
Репозиторий: https://github.com/Rovn00/todo
Первый успешный CI с публикацией образа: https://github.com/Rovn00/todo/actions/runs/38365963629
Для deployment через GitHub ещё требуется подключить self-hosted runner и настроить Secrets. Наличие workflow само по себе не является
доказательством успешного CI: на защите нужна настоящая история Actions.

## Быстрый запуск: Docker Compose

Нужны Docker с запущенным движком, Compose и Python 3 для создания .env.
Все команды выполнять из папки проекта.

```bash
./manage.sh init
docker compose up -d --build
```

init создаёт .env со случайными паролями, существующий .env не перезаписывает.
Далее одна команда Compose запускает приложение, базу, Prometheus и Grafana.

- Приложение: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 — логин admin, пароль GRAFANA_PASSWORD из локального .env.

В Grafana открыть Dashboards → Учебный проект → «Список задач — мониторинг».
Dashboard и источник данных создаются автоматически из файлов chart/files.
Сделать несколько запросов и подождать около минуты, чтобы rate-графики получили данные.

```bash
curl --fail http://localhost:8000/health
curl --fail http://localhost:8000/api/items
curl --fail http://localhost:8000/metrics
docker compose ps
docker compose logs app
docker compose down
```

Последняя команда останавливает контейнеры. Данные остаются в volumes.
`docker compose down -v` также удаляет задачи и историю мониторинга.
Приложение и мониторинг опубликованы только на localhost.

## Docker без Compose

Сначала ./manage.sh init. Загрузить переменные из своего .env, собрать образ и
запустить отдельную базу и приложение в общей сети:

```bash
set -a
. ./.env
set +a
docker build -t todo:local .
docker network create todo-net
docker run -d --name todo-db --network todo-net --network-alias db --env-file .env -e POSTGRES_DB="$DB_NAME" -e POSTGRES_USER="$DB_USER" -e POSTGRES_PASSWORD="$DB_PASSWORD" -v todo-db:/var/lib/postgresql/data postgres:17.6-alpine
```

Дождаться `docker exec todo-db pg_isready -U todo -d todo` с успешным результатом, затем:

```bash
docker run -d --name todo-app --network todo-net --env-file .env -e DB_HOST=db -e DB_PORT=5432 -e PORT=8000 -p 127.0.0.1:8001:8000 todo:local
curl --fail http://localhost:8001/health
docker logs todo-app
docker stop todo-app todo-db
docker rm todo-app todo-db
docker network rm todo-net
```

В примере используется внешний порт 8001, чтобы не мешать Compose на 8000.
Образ — готовые слои Python, зависимостей и кода. Контейнер — запущенный экземпляр образа.
Dockerfile описывает сборку. Порты соединяют компьютер и контейнер.
Переменные окружения меняют настройки без редактирования Python.

## Переменные окружения

| Переменная | Назначение |
| --- | --- |
| PORT | Порт Python-сервера (8000); в .env для Compose — внешний порт компьютера |
| DB_HOST | Хост PostgreSQL: localhost локально, db внутри Compose/Kubernetes |
| DB_PORT | Порт PostgreSQL, по умолчанию 5432 |
| DB_NAME | Имя базы, по умолчанию todo |
| DB_USER | Пользователь базы, по умолчанию todo |
| DB_PASSWORD | Пароль PostgreSQL, обязателен |
| GRAFANA_PASSWORD | Пароль администратора Grafana |

.env.example содержит только примеры. .env и .local исключены из Git и Docker context.
Не добавлять настоящие пароли, токены или kubeconfig в Git.
Смена DB_PASSWORD в .env не меняет пароль уже созданной базы: это надо сделать отдельно
через ALTER ROLE и затем обновить настройки приложения. Для демонстрации конфигурации
проще менять PORT, а не пароль или имя существующей базы.

Изменить PORT=8080 в .env, выполнить `docker compose up -d` и открыть localhost:8080.

## Локальный Kubernetes и Helm

Нужны kubectl, kind и Helm 3. Docker должен работать. На macOS:

```bash
brew install kind helm kubectl
```

Кластер изолирован, его kubeconfig хранится в .local/kubeconfig.

```bash
./manage.sh cluster
./manage.sh deploy
export KUBECONFIG="$PWD/.local/kubeconfig"
./manage.sh status
helm list -n todo
kubectl -n todo get configmap,secret
```

deploy собирает образ с новым локальным tag, загружает его в kind, создаёт Secret
из .env и устанавливает/обновляет chart. helm --wait дожидается готовности ресурсов.
При первой установке скачивание образов может занять несколько минут.
В namespace todo запускаются четыре Deployment: app, db, prometheus, grafana.
Для секретов используется команда `./manage.sh secrets`; пароль не записывается в chart.

Открыть три терминала с тем же KUBECONFIG и выполнить:

```bash
kubectl -n todo port-forward service/app 8002:8000
kubectl -n todo port-forward service/prometheus 9091:9090
kubectl -n todo port-forward service/grafana 3001:3000
```

Приложение доступно на http://localhost:8002, Prometheus — localhost:9091,
Grafana — localhost:3001. Пароль Grafana тот же GRAFANA_PASSWORD из .env.
Остановка port-forward — Ctrl+C. После удаления Pod port-forward может потребовать перезапуска.

```bash
helm lint ./chart
helm template todo ./chart
kubectl -n todo logs deployment/app
kubectl -n todo describe pod -l app=app
kubectl -n todo get events --sort-by=.metadata.creationTimestamp
```

Pod запускает контейнер. Deployment пересоздаёт Pod и обновляет версию.
Service даёт стабильный адрес. ConfigMap хранит обычные настройки.
Secret хранит пароли отдельно от кода (base64 — не шифрование).
PVC сохраняет PostgreSQL при пересоздании Pod.
/health проверяет базу: readinessProbe исключает приложение из Service при проблеме.
/live проверяет живой процесс: livenessProbe перезапускает зависший контейнер.
При недоступной БД процесс остаётся живым, поэтому его не надо бесконечно перезапускать.

В Kubernetes история Prometheus и внутреннее состояние Grafana находятся в emptyDir:
при замене их Pod история теряется, dashboard автоматически восстанавливается из ConfigMap.
Задачи сохраняются отдельно в PVC. Это небольшой учебный кластер, не production-установка.

## Что показывает dashboard

- HTTP-запросы в секунду: rate счётчика todo_http_requests_total.
- Ошибки в секунду: тот же счётчик для статусов 4xx и 5xx.
- Среднее время ответа: прирост суммы времени / прирост числа запросов.
- Доступность /metrics: up=1, если Prometheus может собрать метрики, up=0 при недоступности сервера.

Технические запросы /health, /live и /metrics не входят в пользовательский счётчик.
up показывает доступность сбора метрик, а не соединения с БД. При отказе базы API
возвращает 503 и увеличивает график ошибок, а /metrics остаётся доступным.
У Gunicorn один worker с четырьмя потоками: метрики корректно собираются одним процессом.
Счётчики сбрасываются при перезапуске процесса; Prometheus rate учитывает сброс.

## Проверки приложения

Тестам нужна отдельная база todo_test. Они очищают только базу, имя которой заканчивается на _test.

```bash
docker compose exec db sh -c 'createdb -U "$POSTGRES_USER" todo_test'
docker compose run --rm --no-deps -e DB_NAME=todo_test -v "$PWD/test_app.py:/app/test_app.py:ro" app python -m unittest -v
```

createdb выполнить один раз. Проверяется CRUD, сохранение, плохой ввод, метрики,
ответ 503 при проблемах БД и работа /live. Дополнительно проверить настоящий отказ БД по сценарию ниже.

Для запуска Python без контейнера установить зависимости в venv и подключиться к
доступной PostgreSQL. Compose по умолчанию не публикует порт базы на компьютер.
Можно использовать отдельный контейнер PostgreSQL с `-p 127.0.0.1:5432:5432`,
загрузить переменные из .env и выполнить `python app.py`.

## GitHub Actions, Registry и deployment

Workflow .github/workflows/ci.yaml выполняет:

1. Checkout, установка Python, тесты с настоящей PostgreSQL.
2. Проверка Helm, сборка image, HTTP-проверка контейнера.
3. Создание временного kind, установка chart и проверка /health.
4. После успешной проверки push/main, tag v* или ручной запуск публикует image в GHCR.
5. Ручной запуск на main с галочкой deploy обновляет рабочий Kubernetes.

На pull request публикация и deployment не выполняются.
Образы собираются для amd64 и arm64. Tag `sha-<полный commit>` однозначно указывает версию;
Git tag v1.0.0 дополнительно даёт tag образа v1.0.0.

Для настоящих запусков создать репозиторий на GitHub и отправить код:

```bash
git remote add origin https://github.com/Rovn00/todo.git
git push -u origin main
```

Во вкладке Actions показать успешно завершившиеся check и publish.
Образ публикуется в Packages по адресу ghcr.io/rovn00/todo.
Публикация использует автоматический GITHUB_TOKEN, его не нужно записывать в Git.

Для deployment добавить self-hosted runner с меткой todo через Settings → Actions → Runners.
Runner должен иметь kubectl и helm в PATH, доступ к кластеру и доступ к GHCR.
Для локального kind runner работает на том же компьютере; он должен быть включён
в момент ручного запуска. Обычный GitHub-hosted runner не может обратиться к localhost твоего Mac.

Создать GitHub Environment production и добавить в него Secrets:

| Secret | Значение |
| --- | --- |
| KUBE_CONFIG | Содержимое .local/kubeconfig для runner на этом компьютере |
| DB_PASSWORD | Тот же пароль, что уже использует рабочая база |
| GRAFANA_PASSWORD | Пароль Grafana |
| GHCR_READ_TOKEN | Токен с read:packages для чтения приватного пакета GHCR |

Репозиторий и package должны давать владельцу токена право чтения. Для чужой организации
может понадобиться её сервисный аккаунт вместо github.repository_owner в workflow.
Не менять пароль существующей PostgreSQL просто обновлением Secret.
Runner должен работать только с доверенным кодом этого репозитория.

Actions → CI and Deploy → Run workflow → branch main → deploy=true.
Workflow проверяет и публикует образ, затем создаёт Secret для imagePull,
выполняет helm upgrade и ждёт /health. Историю deployment показать в Actions и `helm history todo -n todo`.
Если runner не подключён, deploy будет ждать в очереди — это не успешный deployment.

## Сценарии защиты

### Пересборка и обновление

```bash
docker compose up -d --build
./manage.sh deploy
helm history todo -n todo
```

Для отката неудачного обновления: `helm rollback todo НОМЕР_ПРЕДЫДУЩЕЙ_РЕВИЗИИ -n todo --wait`.

Изменить, например, заголовок в index.html и повторить deployment.
Для CI выполнить commit и push, показать новый запуск и tag образа.

### Удалить Pod и проверить сохранение

Добавить задачу в Kubernetes-приложении, затем:

```bash
kubectl -n todo delete pod -l app=app
kubectl -n todo rollout status deployment/app --timeout=120s
kubectl -n todo get pods
```

Deployment создаёт новый Pod. Перезапустить port-forward и показать сохранённую задачу.

### База временно недоступна в Compose

```bash
docker compose stop db
curl -i http://localhost:8000/api/items
curl -i http://localhost:8000/health
curl -i http://localhost:8000/live
docker compose logs --tail=30 app
docker compose start db
```

API и health дают 503, live даёт 200. В логах есть «База недоступна».
После запуска базы API и health снова дают 200, задачи сохраняются.

### База временно недоступна в Kubernetes

```bash
kubectl -n todo scale deployment/db --replicas=0
kubectl -n todo get pods -w
```

Приложение становится 0/1 Ready и исключается из Service; liveness не перезапускает его из-за БД.
Посмотреть логи и отсутствие готового адреса у Service:

```bash
kubectl -n todo logs deployment/app --tail=30
kubectl -n todo get endpointslice -l kubernetes.io/service-name=app
kubectl -n todo scale deployment/db --replicas=1
kubectl -n todo rollout status deployment/db --timeout=120s
kubectl -n todo rollout status deployment/app --timeout=120s
```

### Проверить liveness

Приостановить worker Gunicorn внутри Pod, не завершая контейнер:

```bash
kubectl -n todo exec -i deployment/app -- python - <<'PY'
import os
import signal
from pathlib import Path
for process in Path('/proc').iterdir():
    if process.name.isdigit():
        status = (process / 'status').read_text()
        if 'PPid:\t1\n' in status:
            os.kill(int(process.name), signal.SIGSTOP)
PY
kubectl -n todo get pods -w
```

Через несколько неудачных livenessProbe Kubernetes перезапускает контейнер,
RESTARTS увеличивается. Проверить события `kubectl -n todo describe pod -l app=app`.

### Изменить конфигурацию Kubernetes

```bash
helm upgrade todo ./chart -n todo --reuse-values --set app.port=8080 --wait --timeout 5m
```

Меняется ConfigMap, Pod обновляется по checksum, probes и targetPort меняются вместе.
Внешний Service сохраняет порт 8000. Вернуть app.port=8000 той же командой.

### Остановка

```bash
docker compose stop app
docker compose start app
docker compose down
helm uninstall todo -n todo
```

PVC PostgreSQL сохранён намеренно. Его удаление `kubectl -n todo delete pvc todo-postgres`
удаляет задачи. Удаление всего кластера `kind delete cluster --name todo` также уничтожает его данные.

## Полезные первоисточники

- kind: https://kind.sigs.k8s.io/docs/user/quick-start/
- Helm: https://helm.sh/docs/intro/quickstart/
- Prometheus: https://prometheus.io/docs/prometheus/latest/configuration/configuration/
- Grafana provisioning: https://grafana.com/docs/grafana/latest/administration/provisioning/
- GitHub Registry/CI: https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images

На промежуточной проверке объяснить: что добавлено, что работает, какая была проблема,
как её решили и какой командой проверили. На финальной проверке запускать систему,
а не только показывать YAML. Локальные проверки не заменяют историю CI и реальную публикацию.

## Что проверено локально 13.10.2026

- 4 автоматических теста приложения с настоящей PostgreSQL — прошли.
- Docker build и Compose: HTTP, CRUD, сохранение после restart, отказ БД и восстановление — прошли.
- helm lint, проверка workflow через actionlint и проверка конфигурации через promtool — прошли.
- kind: создание кластера, установка и обновление Helm — прошли.
- Удаление Pod, сохранение задач в PVC, readiness при отключении БД — прошли.
- Зависание worker: событие «Container app failed liveness probe, will be restarted» — получено.
- Изменение порта через ConfigMap/Helm и возврат порта — прошли.
- Grafana dashboard, связь datasource с Prometheus, метрики запросов, ошибок и времени — проверены в обеих средах.
- GitHub Actions: check и publish успешно выполнены в запуске https://github.com/Rovn00/todo/actions/runs/38365963629.
- Образ опубликован в ghcr.io/rovn00/todo с tag sha-7739972056f9090b4fd28a7c320e673477e0ff6f.
- Deployment через GitHub ещё не выполнялся: требуется подключить runner и настроить Secrets.
