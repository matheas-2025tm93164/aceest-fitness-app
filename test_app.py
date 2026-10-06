import pytest
from app import app, PROGRAMS, SITE_METRICS

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/health')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'Healthy'

def test_get_all_programs(client):
    response = client.get('/api/programs')
    assert response.status_code == 200
    json_data = response.get_json()
    assert 'fat_loss' in json_data
    assert 'muscle_gain' in json_data
    assert 'beginner' in json_data

def test_get_valid_program(client):
    response = client.get('/api/programs/fat_loss')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['title'] == 'Fat Loss (FL)'
    assert '2,000 kcal' in json_data['diet']

def test_get_invalid_program(client):
    response = client.get('/api/programs/invalid_program')
    assert response.status_code == 404
    json_data = response.get_json()
    assert json_data['error'] == 'Program not found'

def test_site_metrics(client):
    response = client.get('/api/metrics')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['capacity'] == '150 Users'
    assert json_data['area'] == '10,000 sq ft'
    assert json_data['break_even'] == '250 Members'
