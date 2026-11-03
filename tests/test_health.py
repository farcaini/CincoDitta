from fastapi.testclient import TestClient

from cincoditta.main import app


def test_health_usa_il_database(tmp_path, monkeypatch):
    db = tmp_path / "test.db"
    monkeypatch.setenv("CINCODITTA_DB", str(db))

    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert db.exists()


def test_frontend_servito_alla_radice():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "CincoDitta" in response.text
