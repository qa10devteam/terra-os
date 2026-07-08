"""Sprint K9 tests — intelligence endpoints: anomalies, win-probability, run-intelligence."""
import uuid
import pytest

TENANT_ID = "ec3d1e16-2139-48c2-93b5-ffe0defd606d"


@pytest.fixture
def client():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services.api.services.api.routers.kosztorys_v2 import router as k_router
    from services.api.services.api.auth.deps import get_current_user, CurrentUser

    app = FastAPI()
    app.include_router(k_router)

    mock_user = CurrentUser(
        user_id="test-k9", email="test@qa10.io", org_id=TENANT_ID, role="admin",
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    return TestClient(app)


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token", "X-Tenant-Id": TENANT_ID}


@pytest.fixture
def kid(client, auth_headers):
    resp = client.post("/api/v2/kosztorys", json={
        "nazwa": f"K9-Intel-{uuid.uuid4().hex[:6]}",
        "inwestor": "PKP PLK SA",
        "obiekt": "Linia kolejowa E30",
        "ko_r_pct": 70, "ko_s_pct": 30, "z_pct": 10, "kz_pct": 7, "vat_pct": 23,
    }, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture
def kid_with_pozycje(client, auth_headers, kid):
    for i, (opis, jm, ilosc, r, m, s) in enumerate([
        ("Roboty ziemne", "m3", 1000.0, 12.0, 0.0, 15.0),
        ("Beton C30/37", "m3", 200.0, 20.0, 500.0, 40.0),
        ("Stal zbrojeniowa", "t", 10.0, 250.0, 5200.0, 80.0),
    ], start=1):
        client.post(f"/api/v2/kosztorys/{kid}/pozycje", json={
            "lp": i, "opis": opis, "jednostka": jm, "ilosc": ilosc,
            "r_jcena": r, "m_jcena": m, "s_jcena": s,
        }, headers=auth_headers)
    return kid


class TestAnomaliesEndpoint:
    def test_anomalies_empty(self, client, auth_headers, kid):
        resp = client.get(f"/api/v2/kosztorys/{kid}/anomalies", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "anomalies" in body
        assert "count" in body
        assert body["count"] == 0

    def test_anomalies_with_pozycje(self, client, auth_headers, kid_with_pozycje):
        resp = client.get(f"/api/v2/kosztorys/{kid_with_pozycje}/anomalies", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "anomalies" in body
        assert isinstance(body["anomalies"], list)

    def test_anomalies_nonexistent(self, client, auth_headers):
        resp = client.get(f"/api/v2/kosztorys/{uuid.uuid4()}/anomalies", headers=auth_headers)
        assert resp.status_code == 404


class TestWinProbabilityEndpoint:
    def test_win_prob_empty_kosztorys(self, client, auth_headers, kid):
        resp = client.get(f"/api/v2/kosztorys/{kid}/win-probability", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "win_probability" in body
        assert "total_netto" in body

    def test_win_prob_with_cpv(self, client, auth_headers, kid):
        resp = client.get(
            f"/api/v2/kosztorys/{kid}/win-probability?cpv=45200000",
            headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "win_probability" in body

    def test_win_prob_with_pozycje(self, client, auth_headers, kid_with_pozycje):
        # Recalc first
        client.post(f"/api/v2/kosztorys/{kid_with_pozycje}/recalc", headers=auth_headers)
        resp = client.get(f"/api/v2/kosztorys/{kid_with_pozycje}/win-probability", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "kosztorys_id" in body

    def test_win_prob_nonexistent(self, client, auth_headers):
        resp = client.get(f"/api/v2/kosztorys/{uuid.uuid4()}/win-probability", headers=auth_headers)
        assert resp.status_code == 404


class TestRunIntelligence:
    def test_run_intelligence_empty(self, client, auth_headers, kid):
        resp = client.post(f"/api/v2/kosztorys/{kid}/intelligence", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "kosztorys_id" in body

    def test_run_intelligence_with_pozycje(self, client, auth_headers, kid_with_pozycje):
        # Recalc first so suma_netto > 0
        client.post(f"/api/v2/kosztorys/{kid_with_pozycje}/recalc", headers=auth_headers)
        resp = client.post(f"/api/v2/kosztorys/{kid_with_pozycje}/intelligence", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert "kosztorys_id" in body
        # win_probability may be present or have error key — both OK
        assert "win_probability" in body or "win_probability_error" in body

    def test_run_intelligence_nonexistent(self, client, auth_headers):
        resp = client.post(f"/api/v2/kosztorys/{uuid.uuid4()}/intelligence", headers=auth_headers)
        assert resp.status_code == 404
