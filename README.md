[![codecov](https://codecov.io/gh/oscaroguledo/wazire/branch/main/graph/badge.svg)](https://codecov.io/gh/oscaroguledo/wazire)
[![CI](https://github.com/oscaroguledo/wazire/actions/workflows/ci.yml/badge.svg)](https://github.com/oscaroguledo/wazire/actions/workflows/ci.yml)

# Wazire — Online Exam Platform

Wazire is a production-grade multi-tenant online exam platform built for Nigerian tertiary institutions. It provides a full-stack solution for creating, administering, and grading exams at scale.

## Architecture

```
nginx (80/443)
  ├── /api/v1/  →  FastAPI backend (gunicorn + uvicorn workers)
  └── /         →  React/TypeScript SPA (static assets)

Background services:
  ├── worker    — Kafka consumer (grading, answer upsert, dashboard refresh)
  └── scheduler — APScheduler (exam status, pre-load questions, force-submit)

Data stores:
  ├── PostgreSQL (via PgBouncer) — primary OLTP store
  ├── Redis                     — exam question cache, rate limiting, key balancer
  └── Kafka (KRaft)             — async task queue
```

## Quick Start

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- Node.js 20 (for local frontend development)
- Python 3.11 (for local backend development)

### Run with Docker Compose

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
# Edit both .env files with your credentials

docker compose up --build
```

The app will be available at `http://localhost`.

### Local Backend Development

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Local Frontend Development

```bash
cd frontend
npm install
npm run dev
```

## Testing

### Backend

```bash
cd backend
pytest                          # run all tests with coverage
pytest -m unit                  # unit tests only
pytest -m integration           # integration tests only
```

### Frontend

```bash
cd frontend
npm run test                    # run tests once
npm run test:coverage           # run with coverage report
npm run test:watch              # watch mode
```

### End-to-End (Playwright)

```bash
cd frontend
npx playwright install --with-deps
npx playwright test
```

## Environment Variables

See [`backend/.env.example`](backend/.env.example) and [`frontend/.env.example`](frontend/.env.example) for all required variables with descriptions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions, branch strategy, and PR requirements.

## Documentation

- [Docker setup](DOCKER.md)
- [Nigerian tertiary institutions reference](NIGERIAN_TERTIARY_INSTITUTIONS.md)
- [Test infrastructure summary](TEST_INFRASTRUCTURE_SUMMARY.md)
