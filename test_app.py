import os
import unittest
from unittest.mock import patch
import psycopg
from app import app, connect_db


class AppTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.getenv('DB_NAME', '').endswith('_test'):
            raise RuntimeError('Для тестов нужна отдельная DB_NAME с окончанием _test')

    def setUp(self):
        self.client = app.test_client()
        with connect_db() as db:
            db.execute('DELETE FROM tasks')

    def test_tasks(self):
        with self.client.get('/') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/health').json, {'status': 'ok'})
        response = self.client.post('/api/items', json={'text': 'Сделать задание'})
        self.assertEqual(response.status_code, 201)
        task = response.json
        self.assertEqual(self.client.get('/api/items').json, [task])
        with connect_db() as db:
            self.assertEqual(db.execute('SELECT text FROM tasks').fetchone()['text'], task['text'])
        self.assertEqual(self.client.delete('/api/items/' + str(task['id'])).status_code, 200)
        self.assertEqual(self.client.get('/api/items').json, [])
        self.assertEqual(self.client.delete('/api/items/' + str(task['id'])).status_code, 404)

    def test_bad_input(self):
        for data in ({'text': ''}, {'text': ' '}, {'text': 1}, {'text': 'a' * 201}, []):
            self.assertEqual(self.client.post('/api/items', json=data).status_code, 400)
        self.assertEqual(self.client.post('/api/items', data='{', content_type='application/json').status_code, 400)

    def test_database_failure(self):
        with patch('app.connect_db', side_effect=psycopg.OperationalError('test')):
            self.assertEqual(self.client.get('/health').status_code, 503)
            self.assertEqual(self.client.get('/api/items').status_code, 503)
            self.assertEqual(self.client.get('/live').status_code, 200)
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_metrics(self):
        self.client.get('/api/items')
        self.client.post('/api/items', json={'text': ''})
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        metrics = response.get_data(as_text=True)
        self.assertIn('todo_http_requests_total{method="POST",path="/api/items",status="400"}', metrics)
        self.assertIn('todo_http_duration_seconds_count{path="/api/items"}', metrics)


if __name__ == '__main__':
    unittest.main()
