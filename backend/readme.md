# Wazire Backend Setup

## Docker Compose (Recommended)

From the repository root, run:

```bash
docker compose up --build
```

This starts:
- `backend` (FastAPI on port 8000)
- `postgres` (PostgreSQL on port 5432)
- `redis` (Redis on port 6379)
- `celery-worker` (async/background jobs)
- `celery-beat` (scheduled jobs, including exam-status updates and email queue ticks)

Notes:
- Backend container runs `alembic upgrade head` on startup.
- Scheduler in `main.py` is disabled by default (`USE_INTERNAL_SCHEDULER=false`) to avoid double-running jobs when Celery Beat is enabled.

## Setup Instructions

### 1. Install Dependencies
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and configure your settings:
```bash
cp .env.example .env
```

Update the `.env` file with your settings. For database configuration, see [MIGRATIONS.md](./MIGRATIONS.md) for connection details and URL format.

Example `.env` file:
```
DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
SECRET_KEY=your-secret-key-here
```

### 3. Initialize Database Tables
Since you're using PostgreSQL, you need to create the database tables before running the application. See [MIGRATIONS.md](./MIGRATIONS.md) for detailed instructions on:
- Using Alembic migrations (recommended for production)
- Direct table creation with `init_db()` (for development)

Quick start (development):
```bash
python -c "from core.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 4. Run the Application
```bash
python main.py
```

The server will start on `http://0.0.0.0:8000`

### 5. Create Test Data (Optional)
To create test users, a tenant, course, exam, and questions:

```bash
python create_test_users.py
```

This will create:
- **Admin**: admin@greenland.edu / adminpass123
- **Lecturer**: lecturer@greenland.edu / lecturerpass123
- **Students**: student@greenland.edu, student2@greenland.edu / studentpass123
- **Tenant**: Greenland University
- **Course**: Introduction to Computer Science (CS101)
- **Exam**: Computer Science Fundamentals - Final Exam
- **Questions**: 10 multiple choice questions

## Development Notes

- The scheduler is disabled by default (exam status updates) until database tables are created
- After creating tables, you can re-enable the scheduler by setting `with_exam_task=True` in `main.py`
- The application uses SQLAlchemy with async support (asyncpg driver for PostgreSQL)

## Troubleshooting

### "relation does not exist" Error
This means the database tables haven't been created yet. See [MIGRATIONS.md](./MIGRATIONS.md) for instructions on initializing the database.

### Address Already in Use
If you see "Address already in use", another process is using port 8000. Either:
- Stop the other process, or
- Change the PORT in your `.env` file