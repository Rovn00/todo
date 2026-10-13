#!/bin/sh
set -eu
cd "$(dirname "$0")"
export PATH="$PWD/.local/bin:$PATH"

case "${1:-help}" in
  init)
    if [ -f .env ]; then
      echo '.env уже существует, оставлен без изменений'
      exit 0
    fi
    umask 077
    python3 - <<'PY'
import secrets
from pathlib import Path
Path('.env').write_text(
    'PORT=8000\nDB_HOST=localhost\nDB_PORT=5432\nDB_NAME=todo\nDB_USER=todo\n'
    'DB_PASSWORD=' + secrets.token_hex(24) + '\n'
    'GRAFANA_PASSWORD=' + secrets.token_hex(24) + '\n'
)
PY
    echo 'Создан .env со случайными паролями. Он исключён из Git.'
    ;;
  up)
    docker compose up -d --build
    ;;
  down)
    docker compose down
    ;;
  cluster)
    mkdir -p .local
    kind create cluster --name todo --kubeconfig "$PWD/.local/kubeconfig" --wait 120s
    ;;
  secrets)
    test -f .env || { echo 'Сначала ./manage.sh init'; exit 1; }
    set -a
    . ./.env
    set +a
    export KUBECONFIG="${KUBECONFIG:-$PWD/.local/kubeconfig}"
    kubectl create namespace todo --dry-run=client -o yaml | kubectl apply -f -
    kubectl -n todo create secret generic todo-secrets \
      --from-literal=DB_PASSWORD="$DB_PASSWORD" \
      --from-literal=GRAFANA_PASSWORD="$GRAFANA_PASSWORD" \
      --dry-run=client -o yaml | kubectl apply -f -
    ;;
  deploy)
    export KUBECONFIG="${KUBECONFIG:-$PWD/.local/kubeconfig}"
    tag="local-$(date +%s)"
    docker build -t "todo:$tag" .
    kind load docker-image "todo:$tag" --name todo
    "$0" secrets
    helm upgrade --install todo ./chart -n todo \
      --set "image.tag=$tag" --wait --timeout 10m
    ;;
  status)
    export KUBECONFIG="${KUBECONFIG:-$PWD/.local/kubeconfig}"
    kubectl -n todo get pods,svc,pvc
    ;;
  *)
    echo './manage.sh init | up | down | cluster | secrets | deploy | status'
    ;;
esac
