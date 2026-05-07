# Wazire Backend Test Suite

This directory contains the comprehensive test suite for the Wazire backend, covering unit tests, integration tests, and end-to-end scenario tests.

## Test Infrastructure Setup

### Backend (Python/pytest)

**Configuration Files:**
- `backend/pyproject.toml` - pytest and coverage configuration
- `backend/requirements.txt` - includes pytest, pytest-asyncio, pytest-cov, httpx

**Test Structure:**
```
backend/tests/
├── __init__.py
├── README.md (this file)
├── test_bug_condition_exploration.py  # Property 1: Bug condition tests
├── test_preservation_properties.py     # Property 2: Preservation tests
├── unit/                               # Unit tests (mocked dependencies)
│   ├── __init__.py
│   ├── test_utils_encryption.py
│   ├── test_utils_token.py
│   ├── test_utils_sanitization.py
│   ├── test_utils_validation.py
│   ├── test_groq_key_rotator.py
│   ├── test_task_handlers.py
│   ├── test_kafka_consumer_dispatcher.py
│   └── test_models.py
├── integration/                        # Integration tests (real DB, mocked Kafka/Redis)
│   ├── __init__.py
│   ├── conftest.py
│   └── test_auth_routes.py
└── e2e/                                # End-to-end scenario tests
    ├── __init__.py
    └── (to be created)
```

### Frontend (TypeScript/Vitest)

**Configuration Files:**
- `frontend/vitest.config.ts` - Vitest and coverage configuration
- `frontend/src/test-setup.ts` - MSW setup for tests
- `frontend/package.json` - includes vitest, @vitest/coverage-v8, @testing-library/react, msw

**Test Structure:**
```
frontend/src/
├── mocks/
│   ├── handlers.ts  # MSW mock API handlers
│   └── server.ts    # MSW server setup
├── test-setup.ts    # Global test setup
└── (test files to be created alongside source files)
```

## Running Tests

### Backend Tests

**Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

**Run all tests:**
```bash
pytest
```

**Run with coverage:**
```bash
pytest --cov --cov-report=html
```

**Run specific test categories:**
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only (requires TEST_DATABASE_URL)
export TEST_DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/wazire_test"
pytest tests/integration/ -v

# E2E tests only
pytest tests/e2e/ -v

# Bug condition exploration tests
pytest tests/test_bug_condition_exploration.py -v

# Preservation property tests
pytest tests/test_preservation_properties.py -v
```

**Run tests by marker:**
```bash
pytest -m unit      # Unit tests
pytest -m integration  # Integration tests
pytest -m e2e       # E2E tests
pytest -m slow      # Slow tests
```

### Frontend Tests

**Install dependencies:**
```bash
cd frontend
npm install
```

**Run all tests:**
```bash
npm test
```

**Run with coverage:**
```bash
npm run test:coverage
```

**Run in watch mode:**
```bash
npm run test:watch
```

**Run with UI:**
```bash
npm run test:ui
```

## Test Coverage Requirements

Both backend and frontend must maintain **≥90% coverage** across:
- Lines
- Branches
- Functions
- Statements

Coverage reports are generated in:
- Backend: `backend/htmlcov/index.html`
- Frontend: `frontend/coverage/index.html`

## Writing Tests

### Backend Unit Tests

Unit tests should:
- Mock all external dependencies (DB, Redis, Kafka, HTTP clients)
- Test one function/method in isolation
- Be fast (<100ms per test)
- Not import from `main.py` or `worker.py`

**Example:**
```python
import pytest
from unittest.mock import AsyncMock, patch

class TestMyService:
    @pytest.mark.asyncio
    async def test_my_method_success(self):
        """Test that my_method returns expected result."""
        # Arrange
        mock_db = AsyncMock()
        service = MyService(mock_db)
        
        # Act
        result = await service.my_method("input")
        
        # Assert
        assert result == "expected"
```

### Backend Integration Tests

Integration tests should:
- Use a real test PostgreSQL database (TEST_DATABASE_URL)
- Mock Kafka and Redis (via conftest.py fixtures)
- Use httpx.AsyncClient against the FastAPI app
- Test full request/response cycles

**Example:**
```python
import pytest
import httpx

pytestmark = pytest.mark.integration

class TestMyRoute:
    @pytest.mark.asyncio
    async def test_get_endpoint(self, client: httpx.AsyncClient, auth_headers: dict):
        """Test GET /api/v1/my-endpoint returns 200."""
        resp = await client.get("/api/v1/my-endpoint", headers=auth_headers)
        
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
```

### Frontend Unit Tests

Frontend unit tests should:
- Test API functions, utilities, and components in isolation
- Use MSW to mock API responses
- Use @testing-library/react for component tests

**Example:**
```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MyComponent } from './MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
```

### Frontend Integration Tests

Frontend integration tests should:
- Test page components with MSW-mocked API calls
- Verify form submission, navigation, and state management

**Example:**
```typescript
import { describe, it, expect } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from './LoginPage'

describe('LoginPage', () => {
  it('logs in successfully', async () => {
    render(<LoginPage />)
    
    await userEvent.type(screen.getByLabelText('Email'), 'test@test.com')
    await userEvent.type(screen.getByLabelText('Password'), 'password')
    await userEvent.click(screen.getByRole('button', { name: 'Login' }))
    
    await waitFor(() => {
      expect(screen.getByText('Welcome')).toBeInTheDocument()
    })
  })
})
```

## Test Database Setup

Integration tests require a test PostgreSQL database. Create it with:

```bash
createdb wazire_test
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/wazire_test"
```

Run migrations on the test database:
```bash
cd backend
alembic upgrade head
```

## Continuous Integration

Tests run automatically on every push and pull request via GitHub Actions (`.github/workflows/ci.yml`).

CI pipeline includes:
1. Backend linting (ruff)
2. Backend type checking (mypy)
3. Backend tests with coverage
4. Frontend linting (eslint)
5. Frontend type checking (tsc)
6. Frontend tests with coverage
7. Playwright E2E tests
8. Coverage upload to Codecov

## Test Markers

Backend tests use pytest markers for categorization:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (real DB)
- `@pytest.mark.e2e` - End-to-end scenario tests
- `@pytest.mark.slow` - Tests that take >1 second

## Troubleshooting

**"No module named 'pytest'"**
- Run `pip install -r requirements.txt` in the backend directory

**"Connection refused" errors in integration tests**
- Ensure TEST_DATABASE_URL points to a running PostgreSQL instance
- Check that the test database exists and migrations are applied

**Frontend tests fail with "fetch is not defined"**
- Ensure `jsdom` is installed: `npm install --save-dev jsdom`
- Check that `vitest.config.ts` has `environment: 'jsdom'`

**MSW handlers not intercepting requests**
- Verify `src/test-setup.ts` is listed in `vitest.config.ts` setupFiles
- Check that MSW server is started in beforeAll hook

## Next Steps

To complete the test suite:

1. **Backend:**
   - Add service unit tests for all services in `services/`
   - Add integration tests for all API routes
   - Add E2E scenario tests (full exam lifecycle, force submit, concurrent UPSERT)

2. **Frontend:**
   - Add unit tests for all API functions in `apis/*.ts`
   - Add unit tests for all utility functions in `utils/*.ts`
   - Add component tests for all shared components
   - Add integration tests for all page components
   - Add Playwright E2E tests for critical user paths

3. **CI/CD:**
   - Set up GitHub Actions workflow (`.github/workflows/ci.yml`)
   - Configure Codecov integration
   - Add coverage badge to README.md

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Testing Library documentation](https://testing-library.com/)
- [MSW documentation](https://mswjs.io/)
- [Playwright documentation](https://playwright.dev/)
