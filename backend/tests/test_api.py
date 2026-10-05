from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'

def test_demo_meeting_has_grounded_data():
    response = client.get('/api/meetings/apollo-demo')
    assert response.status_code == 200
    data = response.json()
    assert len(data['decisions']) == 3
    assert all(item['timestamp'] and item['evidence'] for item in data['decisions'])

def test_ask_refuses_unknown_facts():
    response = client.post('/api/meetings/apollo-demo/ask', json={'question': 'What was the office catering vendor?'})
    assert response.status_code == 200
    assert response.json()['evidence'] == []
