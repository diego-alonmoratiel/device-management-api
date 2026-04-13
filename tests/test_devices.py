import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.database import Base, get_db

# Base de datos en memoria para tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(TEST_DATABASE_URL)
AsyncSessionTest = async_sessionmaker(engine_test, expire_on_commit=False)

async def override_get_db():
    async with AsyncSessionTest() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as c:
        yield c


# Health
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# Devices
async def test_create_device(client):
    response = await client.post("/devices/", json={
        "name": "node-01",
        "type": "server",
        "location": "rack-A"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "node-01"
    assert data["status"] == "ONLINE"

async def test_list_devices_empty(client):
    response = await client.get("/devices/")
    assert response.status_code == 200
    assert response.json() == []

async def test_list_devices(client):
    await client.post("/devices/", json={"name": "node-01", "type": "server"})
    await client.post("/devices/", json={"name": "node-02", "type": "server"})
    response = await client.get("/devices/")
    assert len(response.json()) == 2

async def test_get_device(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    response = await client.get(f"/devices/{device_id}")
    assert response.status_code == 200
    assert response.json()["id"] == device_id

async def test_get_device_not_found(client):
    response = await client.get("/devices/999")
    assert response.status_code == 404

async def test_update_device_status(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    response = await client.patch(f"/devices/{device_id}/status", json={"status": "OFFLINE"})
    assert response.status_code == 200
    assert response.json()["status"] == "OFFLINE"


# Metrics
async def test_create_metric(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    response = await client.post(f"/devices/{device_id}/metrics", json={
        "key": "cpu_usage",
        "value": 45.0,
        "unit": "%"
    })
    assert response.status_code == 201
    assert response.json()["value"] == 45.0

async def test_metric_device_not_found(client):
    response = await client.post("/devices/999/metrics", json={
        "key": "cpu_usage",
        "value": 45.0
    })
    assert response.status_code == 404

async def test_list_metrics(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    await client.post(f"/devices/{device_id}/metrics", json={"key": "cpu_usage", "value": 40.0})
    await client.post(f"/devices/{device_id}/metrics", json={"key": "ram_usage", "value": 50.0})
    response = await client.get(f"/devices/{device_id}/metrics")
    assert len(response.json()) == 2


# Alerts
async def test_alert_created_on_warning_threshold(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    await client.post(f"/devices/{device_id}/metrics", json={
        "key": "cpu_usage",
        "value": 85.0
    })
    response = await client.get("/alerts/")
    assert len(response.json()) == 1
    assert response.json()[0]["severity"] == "WARNING"

async def test_alert_created_on_critical_threshold(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    await client.post(f"/devices/{device_id}/metrics", json={
        "key": "cpu_usage",
        "value": 96.0
    })
    response = await client.get("/alerts/")
    assert response.json()[0]["severity"] == "CRITICAL"

async def test_no_alert_below_threshold(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    await client.post(f"/devices/{device_id}/metrics", json={
        "key": "cpu_usage",
        "value": 50.0
    })
    response = await client.get("/alerts/")
    assert response.json() == []

async def test_resolve_alert(client):
    created = await client.post("/devices/", json={"name": "node-01", "type": "server"})
    device_id = created.json()["id"]
    await client.post(f"/devices/{device_id}/metrics", json={
        "key": "cpu_usage",
        "value": 85.0
    })
    alerts = await client.get("/alerts/")
    alert_id = alerts.json()[0]["id"]
    response = await client.patch(f"/alerts/{alert_id}/resolve")
    assert response.status_code == 200
    assert response.json()["resolved"] == True
    # Verificar que ya no aparece en alertas activas
    active = await client.get("/alerts/")
    assert active.json() == []