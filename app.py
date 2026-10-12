import os
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, request, send_file

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 4096
DB_PATH = os.getenv('DB_PATH', 'data/tasks.db')
PORT = int(os.getenv('PORT', '8000'))

Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(DB_PATH) as db:
    db.execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, text TEXT NOT NULL)')


@app.route('/')
def index():
    return send_file(Path(__file__).with_name('index.html'))


@app.route('/api/items')
def get_tasks():
    with sqlite3.connect(DB_PATH) as db:
        rows = db.execute('SELECT id, text FROM tasks ORDER BY id DESC').fetchall()
    return jsonify([{'id': row[0], 'text': row[1]} for row in rows])


@app.route('/api/items', methods=['POST'])
def add_task():
    data = request.get_json(silent=True)
    text = data.get('text') if isinstance(data, dict) else None
    if not isinstance(text, str) or not 1 <= len(text.strip()) <= 200:
        return jsonify(error='Введите задачу от 1 до 200 символов'), 400
    with sqlite3.connect(DB_PATH) as db:
        task = db.execute('INSERT INTO tasks (text) VALUES (?)', (text.strip(),))
        task_id = task.lastrowid
    return jsonify(id=task_id, text=text.strip()), 201


@app.route('/api/items/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    with sqlite3.connect(DB_PATH) as db:
        result = db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    if result.rowcount == 0:
        return jsonify(error='Задача не найдена'), 404
    return jsonify(deleted=True)


@app.route('/health')
def health():
    with sqlite3.connect(DB_PATH) as db:
        db.execute('SELECT COUNT(*) FROM tasks').fetchone()
    return jsonify(status='ok')


@app.errorhandler(sqlite3.Error)
def database_error(error):
    app.logger.error('Ошибка базы данных: %s', error)
    return jsonify(error='База данных недоступна'), 503


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
