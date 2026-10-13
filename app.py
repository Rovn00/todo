import logging
import os
import time
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from flask import Flask, Response, g, jsonify, request, send_file
from prometheus_client import Counter, Histogram, CONTENT_TYPE_LATEST, generate_latest

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4096
logging.basicConfig(level=logging.INFO)
PORT = int(os.getenv('PORT', '8000'))
REQUESTS = Counter('todo_http_requests_total', 'HTTP requests', ['method', 'path', 'status'])
DURATION = Histogram('todo_http_duration_seconds', 'HTTP response time', ['path'])


def connect_db():
    db = psycopg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        dbname=os.getenv('DB_NAME', 'todo'),
        user=os.getenv('DB_USER', 'todo'),
        password=os.environ['DB_PASSWORD'],
        connect_timeout=3,
        row_factory=dict_row
    )
    # Создаём таблицу, если приложение запущено впервые.
    try:
        db.execute('CREATE TABLE IF NOT EXISTS tasks (id SERIAL PRIMARY KEY, text TEXT NOT NULL)')
    except Exception:
        db.close()
        raise
    return db


@app.before_request
def start_request():
    g.started = time.monotonic()


@app.after_request
def count_request(response):
    # Не считаем технические запросы мониторинга и probes.
    if request.path not in ('/metrics', '/live', '/health'):
        path = request.url_rule.rule if request.url_rule else 'unknown'
        REQUESTS.labels(request.method, path, str(response.status_code)).inc()
        DURATION.labels(path).observe(time.monotonic() - g.started)
        app.logger.info('%s %s %s', request.method, request.path, response.status_code)
    return response


@app.route('/')
def index():
    return send_file(Path(__file__).with_name('index.html'))


@app.route('/api/items')
def get_tasks():
    with connect_db() as db:
        tasks = db.execute('SELECT id, text FROM tasks ORDER BY id DESC').fetchall()
    return jsonify(tasks)


@app.route('/api/items', methods=['POST'])
def add_task():
    data = request.get_json(silent=True)
    text = data.get('text') if isinstance(data, dict) else None
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 200:
        return jsonify(error='Введите задачу от 1 до 200 символов'), 400
    with connect_db() as db:
        task = db.execute(
            'INSERT INTO tasks (text) VALUES (%s) RETURNING id, text', (text.strip(),)
        ).fetchone()
    return jsonify(task), 201


@app.route('/api/items/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    with connect_db() as db:
        task = db.execute('DELETE FROM tasks WHERE id = %s RETURNING id', (task_id,)).fetchone()
    if not task:
        return jsonify(error='Задача не найдена'), 404
    return jsonify(deleted=True)


@app.route('/health')
def health():
    with connect_db() as db:
        db.execute('SELECT 1')
    return jsonify(status='ok')


@app.route('/live')
def live():
    return jsonify(status='ok')


@app.route('/metrics')
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


@app.errorhandler(psycopg.Error)
def database_error(error):
    app.logger.error('База недоступна (%s)', type(error).__name__)
    return jsonify(error='База данных недоступна'), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
