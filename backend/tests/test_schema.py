from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'schema.db'}")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.main import app

    return TestClient(app)


def test_mehta_snapshot_comes_from_tables(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        accounts = client.get("/v1/accounts").json()
        mehta = next(row for row in accounts if row["account_number"] == "9A4K2M")
        assert mehta["ship_from_postals"] == ["400001"]
        assert mehta["linked_user_ids"] == ["mehta.ops"]
        assert mehta["inbound_policy"] == "deny_third_party"
        northwind = next(row for row in accounts if row["account_number"] == "2LX8QP")
        assert "110001" in northwind["ship_from_postals"]


def test_same_tx_does_not_create_a_second_decision(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        booking = next(item for item in client.get("/v1/scenarios").json() if item["id"] == "normal")["booking"]
        booking = {**booking, "tx_id": "tx-mehta-1"}
        first = client.post("/v1/booking-risk", json=booking).json()
        second = client.post("/v1/booking-risk", json=booking).json()
        assert first["tx_id"] == second["tx_id"] == "tx-mehta-1"
        assert client.get("/v1/decisions").json().__len__() == 1


def test_review_is_stored_beside_the_decision(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        booking = next(item for item in client.get("/v1/scenarios").json() if item["id"] == "lane")["booking"]
        booking = {**booking, "tx_id": "tx-lane-1"}
        decision = client.post("/v1/booking-risk", json=booking).json()
        assert decision["decision"] == "hold"
        reviewed = client.post(
            "/v1/decisions/tx-lane-1/review",
            json={"reviewer": "anita", "action": "release", "note": "Mehta confirmed this export."},
        )
        assert reviewed.status_code == 200
        body = reviewed.json()
        assert body["decision"] == "hold"
        assert body["reviews"][0]["action"] == "release"
        assert body["reviews"][0]["reviewer"] == "anita"
