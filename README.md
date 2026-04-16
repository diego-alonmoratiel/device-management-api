# Device Management API
[![pipeline status](https://gitlab.com/diego-alonmoratiel-group/API_DEVICES_STATUS/badges/main/pipeline.svg)](https://gitlab.com/diego-alonmoratiel-group/API_DEVICES_STATUS/-/pipelines)
[![coverage](https://gitlab.com/diego-alonmoratiel-group/API_DEVICES_STATUS/badges/main/coverage.svg)](https://gitlab.com/diego-alonmoratiel-group/API_DEVICES_STATUS/-/pipelines)

REST API for registering and monitoring the status of infrastructure devices.
Built with FastAPI and deployed on Kubernetes via Helm.

## Stack

- **FastAPI** — async REST API with Pydantic validation
- **SQLAlchemy 2.0** — async ORM with SQLite
- **Docker + Docker Compose** — local development
- **Kubernetes + Helm** — production deployment
- **GitLab CI/CD** — lint, test, and build pipeline

## Architecture

```
                    ┌─────────────────────────────────────────┐
                    │              K3s Cluster                │
                    │                                         │
          HTTP      │  ┌─────────┐       ┌─────────────────┐  │
Client ──────────▶ │   │ Traefik │─────▶│   FastAPI Pod   │  │
  (device-api.local)│  │ Ingress │       │                 │  │
                    │  └─────────┘       │  /devices       │  │ 
                    │                    │  /metrics       │  │
                    │                    │  /alerts        │  │ 
                    │                    │  /health        │  │
                    │                    └───────┬─────────┘  │
                    │                            │            │
                    │                    ┌───────▼─────────┐  │
                    │                    │  emptyDir volume│  │
                    │                    │   (SQLite DB)   │  │
                    │                    └─────────────────┘  │
                    │                                         │
                    └─────────────────────────────────────────┘

```
## Features

- Register and manage devices with status tracking (ONLINE/OFFLINE/FAULT)
- Submit periodic metrics per device (cpu_usage, memory_usage, temperature, disk_usage)
- Automatic alert generation when metrics exceed configurable thresholds
- Alert resolution workflow
- Liveness and readiness probes on `/health`

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Liveness and readiness probe |
| GET | `/devices` | List all devices |
| POST | `/devices` | Register a new device |
| GET | `/devices/{id}` | Get device details |
| PATCH | `/devices/{id}/status` | Update device status |
| POST | `/devices/{id}/metrics` | Submit a metric reading |
| GET | `/devices/{id}/metrics` | List device metrics |
| GET | `/alerts` | List active alerts |
| PATCH | `/alerts/{id}/resolve` | Resolve an alert |

## Local Development

**Requirements:** Docker, Docker Compose

```bash
git clone https://github.com/diego-alonmoratiel/API_DEVICES_STATUS.git
cd device-management-api

docker compose up
```

API available at `http://localhost:8000`

## Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v --cov=app --cov-report=term-missing
```

## Kubernetes Deployment

**Requirements:** Kubernetes cluster, Helm 3, kubectl

```bash
# Install
helm install device-api ./helm/device-management-api

# Verify
kubectl get pods
kubectl get ingress

# Access (add to /etc/hosts first)
# <node-ip> device-api.local
curl http://device-api.local/health
```

**Upgrade after image change:**

```bash
helm upgrade device-api ./helm/device-management-api \
  --set image.tag=<new-tag>
```

**Uninstall:**

```bash
helm uninstall device-api
```

## Helm Chart Configuration

Key parameters in `values.yaml`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `replicaCount` | `1` | Number of pod replicas |
| `image.repository` | `diegoalonmoratiel/device-management-api` | Image repository |
| `image.tag` | `latest` | Image tag |
| `ingress.enabled` | `true` | Enable ingress |
| `ingress.host` | `device-api.local` | Ingress hostname |
| `resources.limits.cpu` | `200m` | CPU limit |
| `resources.limits.memory` | `256Mi` | Memory limit |
| `nodeSelector.kubernetes.io/hostname` | `desktop-0ftoa8j` | Node Selection **(Should be changed depending on the environment)** |

## CI/CD Pipeline

Three stages run on every push:

- **lint** — flake8 code style check
- **test** — pytest with coverage report
- **build** — Docker image build and push to GitLab Registry (main branch only)

## Technical Decisions

**Async SQLAlchemy with aiosqlite**
FastAPI is async-native. Using a synchronous ORM would block the event loop under load. SQLAlchemy 2.0 with aiosqlite keeps the entire request lifecycle non-blocking.

**emptyDir volume for SQLite**
Kubernetes container filesystems are read-only by default in K3s. SQLite needs a writable directory at runtime, which emptyDir provides. In a production environment this would be replaced with a PersistentVolumeClaim backed by a storage class.

**Helm chart over raw manifests**
Parameterizing the deployment via Helm separates configuration from infrastructure definition. The same chart can target different environments by overriding values without modifying templates.

**Image tagged with commit SHA**
Every image in the registry is traceable to the exact commit that produced it. This enables precise rollbacks and avoids the ambiguity of mutable tags like latest in production.
