import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_combined_demo_job_contract():
    tasks = client.get('/api/tasks').json()
    assert tasks['tasks'][0]['task_id'] == 'T002-today'
    assert tasks['tasks'][0]['demo_seed'] == 170923

    started = client.post('/api/jobs/T002-today/start').json()
    assert started['seed'] == 170923
    assert started['job_id'] == 'T002-today'

    review = client.post(
        '/api/jobs/T002-today/review',
        json={
            'transcript': 'I think the task went smoothly. I felt confident and reacted quickly when the nearby worker appeared.',
            'actual_minutes': 606,
        },
    )
    assert review.status_code == 200
    body = review.json()
    assert body['grade']['objective_score'] == 58
    assert body['calibration_gap'] == 29
    assert body['state'] == 'BLIND_SPOT'
    assert body['recommendation']['recommended_scenario'] == 'Proximity Hazard Response'


def test_api_rejects_unknown_sim_module():
    response = client.post('/api/sim-attempts', json={'module_id': 'not-a-module', 'score': 80})
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'unknown_module'


def test_ml_down_review_preserves_recommendation(monkeypatch):
    monkeypatch.setenv('ML_FORCE_DOWN', '1')
    response = client.post('/api/jobs/T002-today/review', json={'transcript': 'I felt confident.'})
    assert response.status_code == 202
    body = response.json()
    assert body['grade'] is None
    assert body['needs_review'] is True
    assert body['recommendation']['recommended_scenario'] == 'Proximity Hazard Response'
    assert body['fallback_recommendation']['recommended_scenario'] == 'Proximity Hazard Response'
    assert body['fallback_used'] is True
