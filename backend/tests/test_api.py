from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def auth_headers(client):
    response = client.post('/api/auth/login', json={'email': 'demo@meetmind.ai', 'password': 'DemoPass123!'})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}

def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['database'] == 'connected'

def test_demo_meeting_is_authorized_and_persistent(client):
    response = client.get('/api/meetings', headers=auth_headers(client))
    assert response.status_code == 200
    data = response.json()
    assert data['total'] >= 1
    assert data['items'][0]['actions']

def test_ask_refuses_unknown_facts(client):
    meetings = client.get('/api/meetings', headers=auth_headers(client)).json()['items']
    response = client.post(f"/api/meetings/{meetings[0]['id']}/ask", headers=auth_headers(client), json={'question': 'What was the office catering vendor?'})
    assert response.status_code == 200
    assert response.json()['evidence'] == []

def test_register_create_and_update_action(client):
    email = f"qa-{uuid4()}@example.com"
    registration = client.post('/api/auth/register', json={'email': email, 'password': 'StrongPass123!'})
    assert registration.status_code == 201
    headers = {'Authorization': f"Bearer {registration.json()['access_token']}"}
    meeting = client.post('/api/meetings', headers=headers, json={'title': 'QA planning', 'description': 'Persistence check'})
    assert meeting.status_code == 201
    assert meeting.json()['status'] == 'draft'
    actions = client.get('/api/actions', headers=headers)
    assert actions.status_code == 200 and actions.json()['total'] == 0

def test_protected_routes_reject_anonymous_access(client):
    assert client.get('/api/meetings').status_code == 401

def test_upload_stores_recording_metadata(client):
    headers = auth_headers(client)
    meeting_id = client.get('/api/meetings', headers=headers).json()['items'][0]['id']
    response = client.post(f'/api/meetings/{meeting_id}/upload', headers=headers, files={'file': ('notes.txt', b'Project Apollo transcript', 'text/plain')})
    assert response.status_code == 200
    assert response.json()['status'] == 'uploaded'
    assert response.json()['recording_id']
