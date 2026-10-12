import os
import sqlite3
import tempfile
import unittest

folder = tempfile.TemporaryDirectory()
os.environ['DB_PATH'] = os.path.join(folder.name, 'test.db')
from app import app, DB_PATH


class AppTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with sqlite3.connect(DB_PATH) as db:
            db.execute('DELETE FROM tasks')

    def test_tasks(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        self.assertEqual(self.client.get('/health').json, {'status': 'ok'})
        response = self.client.post('/api/items', json={'text': 'Сделать задание'})
        self.assertEqual(response.status_code, 201)
        task = response.json
        self.assertEqual(self.client.get('/api/items').json, [task])
        # Новое подключение к БД видит сохранённую задачу.
        with sqlite3.connect(DB_PATH) as db:
            self.assertEqual(db.execute('SELECT text FROM tasks').fetchone()[0], task['text'])
        self.assertEqual(self.client.delete('/api/items/' + str(task['id'])).status_code, 200)
        self.assertEqual(self.client.get('/api/items').json, [])
        self.assertEqual(self.client.delete('/api/items/' + str(task['id'])).status_code, 404)

    def test_bad_input(self):
        for data in ({'text': ''}, {'text': ' '}, {'text': 1}, {'text': 'a' * 201}, []):
            self.assertEqual(self.client.post('/api/items', json=data).status_code, 400)
        self.assertEqual(self.client.post('/api/items', data='{', content_type='application/json').status_code, 400)

    def test_database_failure(self):
        os.rename(DB_PATH, DB_PATH + '.backup')
        try:
            self.assertEqual(self.client.get('/health').status_code, 503)
        finally:
            os.remove(DB_PATH)
            os.rename(DB_PATH + '.backup', DB_PATH)
        self.assertEqual(self.client.get('/health').status_code, 200)


if __name__ == '__main__':
    unittest.main()
