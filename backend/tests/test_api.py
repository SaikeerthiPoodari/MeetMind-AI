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
    assert next(item for item in data['items'] if item['is_demo'])['actions']

def test_ask_refuses_unknown_facts(client):
    meetings = client.get('/api/meetings', headers=auth_headers(client)).json()['items']
    demo = next(item for item in meetings if item['is_demo'])
    response = client.post(f"/api/meetings/{demo['id']}/ask", headers=auth_headers(client), json={'question': 'What was the office catering vendor?'})
    assert response.status_code == 200
    assert response.json()['evidence'] == []

def test_ask_retrieves_evidence_and_persists_history(client):
    headers = auth_headers(client)
    demo = next(item for item in client.get('/api/meetings', headers=headers).json()['items'] if item['is_demo'])
    response = client.post(f"/api/meetings/{demo['id']}/ask", headers=headers, json={'question': 'What did we decide about PostgreSQL reporting?'})
    assert response.status_code == 200
    assert response.json()['evidence']
    history = client.get(f"/api/meetings/{demo['id']}/questions/history", headers=headers)
    assert history.status_code == 200
    assert any(item['id'] == response.json()['question_id'] for item in history.json()['items'])

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
    assert response.json()['status'] == 'analyzed'
    assert response.json()['recording_id']
    assert response.json()['segments_created'] == 1

def test_search_and_exports_are_authorized(client):
    headers = auth_headers(client)
    demo = next(item for item in client.get('/api/meetings', headers=headers).json()['items'] if item['is_demo'])
    search = client.get('/api/search?q=PostgreSQL', headers=headers)
    assert search.status_code == 200
    assert search.json()['total'] >= 1
    exported = client.get(f"/api/meetings/{demo['id']}/export?format=json", headers=headers)
    assert exported.status_code == 200
    assert exported.headers['content-type'].startswith('application/json')
    assert 'transcript' in exported.json()
    text_export = client.get(f"/api/meetings/{demo['id']}/export?format=txt", headers=headers)
    assert text_export.status_code == 200
    assert 'TRANSCRIPT' in text_export.text

def test_meeting_lifecycle_persists_session(client):
    headers = auth_headers(client)
    demo = next(item for item in client.get('/api/meetings', headers=headers).json()['items'] if item['is_demo'])
    joined = client.post(f"/api/meetings/{demo['id']}/join", headers=headers)
    assert joined.status_code == 200 and joined.json()['status'] == 'joined'
    started = client.post(f"/api/meetings/{demo['id']}/start", headers=headers)
    assert started.json()['status'] == 'live'
    ended = client.post(f"/api/meetings/{demo['id']}/end", headers=headers)
    assert ended.json()['status'] == 'processing'

def test_translation_is_explicitly_unconfigured_without_provider(client):
    headers = auth_headers(client)
    demo = next(item for item in client.get('/api/meetings', headers=headers).json()['items'] if item['is_demo'])
    response = client.post(f"/api/meetings/{demo['id']}/translate", headers=headers, json={'target_language': 'hi', 'scope': 'summary'})
    assert response.status_code == 503
    assert 'not configured' in response.json()['detail'].lower()

def test_user_preferences_are_persisted_and_validated(client):
    headers = auth_headers(client)
    current = client.get('/api/me', headers=headers)
    assert current.status_code == 200 and current.json()['language'] == 'en'
    updated = client.patch('/api/me', headers=headers, json={'language': 'hi', 'timezone': 'Asia/Calcutta', 'notifications_enabled': False})
    assert updated.status_code == 200
    assert updated.json()['language'] == 'hi'
    assert client.patch('/api/me', headers=headers, json={'language': 'xx'}).status_code == 422
