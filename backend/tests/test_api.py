import os

from fastapi.testclient import TestClient


def test_confirm_flow_and_queue(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    # Import after the database path is set. Lifespan reads it on startup.
    from app.main import app

    with TestClient(app) as client:
        health = client.get("/v1/health")
        assert health.status_code == 200
        assert health.json()["model"] == "xgboost"

        heavy = next(item for item in client.get("/v1/scenarios").json() if item["id"] == "heavy")
        first = client.post("/v1/booking-risk", json=heavy["booking"])
        assert first.status_code == 200
        body = first.json()
        assert body["decision"] == "hold"
        assert "MODEL_ELEVATED_SCORE" in body["reason_codes"]
        assert body["explanation_source"] == "rules"
        assert body["billed_account"] == "6LIGHT2"

        normal = next(item for item in client.get("/v1/scenarios").json() if item["id"] == "normal")
        second = client.post("/v1/booking-risk", json=normal["booking"])
        assert second.status_code == 200
        assert second.json()["decision"] == "allow"

        queue = client.get("/v1/decisions").json()
        assert [row["tx_id"] for row in queue][:2] == [second.json()["tx_id"], body["tx_id"]]

        reset = client.post("/v1/reset")
        assert reset.status_code == 200
        assert client.get("/v1/decisions").json() == []


def test_velocity_uses_the_seeded_burst(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'rush.db'}")
    from app.main import app

    with TestClient(app) as client:
        item = next(row for row in client.get("/v1/scenarios").json() if row["id"] == "velocity")
        response = client.post("/v1/booking-risk", json=item["booking"])
        assert response.status_code == 200
        assert response.json()["decision"] == "hold"
        assert "VELOCITY_SPIKE" in response.json()["reason_codes"]
